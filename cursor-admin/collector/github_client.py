"""
GitHub API client — create repos, push Hook files, single point for all GitHub operations.

Supports: create repository (org or user), push initial Hook files via Contents API,
re-inject Hook files. Member management (invite by username) can be added later.
"""

import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from config import settings

log = logging.getLogger(__name__)

HOOK_TEMPLATES_DIR = Path(__file__).parent / "hook_templates"


@dataclass
class GitHubRepo:
    repo_full_name: str  # owner/name
    repo_url: str
    repo_ssh_url: str
    web_url: str
    default_branch: str


class GitHubError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class GitHubClient:
    """Thin wrapper around GitHub REST API (v3)."""

    def __init__(
        self,
        token: str | None = None,
        org: str | None = None,
        default_branch: str | None = None,
    ):
        self.token = token or settings.github_token
        self.org = (org or settings.github_org or "").strip() or None
        self.default_branch = default_branch or "main"

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
    ) -> dict | list | None:
        url = f"https://api.github.com{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            log.error("GitHub API %s %s → %s: %s", method, path, exc.code, detail[:300])
            raise GitHubError(
                f"GitHub API error {exc.code}: {detail[:500]}",
                status_code=exc.code,
            ) from exc
        except urllib.error.URLError as exc:
            log.error("GitHub API unreachable: %s", exc.reason)
            raise GitHubError(f"GitHub unreachable: {exc.reason}") from exc

    def is_configured(self) -> bool:
        return bool(self.token)

    def create_repo(
        self,
        name: str,
        repo_slug: str,
        description: str = "",
        private: bool = True,
    ) -> GitHubRepo:
        """Create a new repository under org (if set) or token owner."""
        if self.org:
            body = {
                "name": repo_slug,
                "description": description,
                "private": private,
                "auto_init": False,
            }
            result = self._request("POST", f"/orgs/{self.org}/repos", body)
            full_name = f"{self.org}/{repo_slug}"
        else:
            body = {
                "name": repo_slug,
                "description": description,
                "private": private,
                "auto_init": False,
            }
            result = self._request("POST", "/user/repos", body)
            full_name = result.get("full_name", f"{result.get('owner', {}).get('login', '')}/{repo_slug}")

        default_branch = result.get("default_branch") or self.default_branch
        return GitHubRepo(
            repo_full_name=full_name,
            repo_url=result.get("clone_url", ""),
            repo_ssh_url=result.get("ssh_url", ""),
            web_url=result.get("html_url", ""),
            default_branch=default_branch,
        )

    def _build_hook_files(self, collector_url: str, project_id: int) -> dict[str, str]:
        """Same structure as GitLab client: path -> content."""
        files: dict[str, str] = {}

        hooks_json_path = HOOK_TEMPLATES_DIR / "hooks.json"
        if hooks_json_path.exists():
            files[".cursor/hooks.json"] = hooks_json_path.read_text(encoding="utf-8")

        hook_py_path = HOOK_TEMPLATES_DIR / "cursor_hook.py"
        if hook_py_path.exists():
            files[".cursor/hook/cursor_hook.py"] = hook_py_path.read_text(encoding="utf-8")

        config_tmpl_path = HOOK_TEMPLATES_DIR / "hook_config.json.tmpl"
        if config_tmpl_path.exists():
            tmpl = config_tmpl_path.read_text(encoding="utf-8")
            rendered = tmpl.replace("{{collector_url}}", collector_url)
            rendered = rendered.replace("{{project_id}}", str(project_id))
            files[".cursor/hook/hook_config.json"] = rendered

        gitignore_tmpl_path = HOOK_TEMPLATES_DIR / "gitignore.tmpl"
        if gitignore_tmpl_path.exists():
            files[".gitignore"] = gitignore_tmpl_path.read_text(encoding="utf-8")

        return files

    def _put_file(
        self,
        repo_full_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> None:
        """Create or update a single file. If sha is set, update; else create."""
        body: dict = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        owner, repo = repo_full_name.split("/", 1)
        encoded_path = urllib.parse.quote(path, safe="")
        self._request("PUT", f"/repos/{owner}/{repo}/contents/{encoded_path}", body)

    def _get_file_sha(self, repo_full_name: str, path: str, branch: str) -> str | None:
        try:
            owner, repo = repo_full_name.split("/", 1)
            encoded_path = urllib.parse.quote(path, safe="")
            result = self._request(
                "GET",
                f"/repos/{owner}/{repo}/contents/{encoded_path}?ref={urllib.parse.quote(branch, safe='')}",
            )
            if isinstance(result, dict) and result.get("sha"):
                return result["sha"]
        except GitHubError as exc:
            if exc.status_code == 404:
                return None
            raise
        return None

    def push_initial_commit(
        self,
        repo_full_name: str,
        collector_url: str,
        project_id: int,
        branch: str | None = None,
    ) -> None:
        """Create Hook files in the repo (and .gitignore) via Contents API."""
        target_branch = branch or self.default_branch
        files = self._build_hook_files(collector_url, project_id)
        for path, content in files.items():
            self._put_file(
                repo_full_name,
                path,
                content,
                "chore: initialize project with Cursor Hook\n\nAuto-generated by Sierac-tm platform.",
                target_branch,
            )
        log.info("Pushed initial commit to GitHub repo %s", repo_full_name)

    def inject_hook_files(
        self,
        repo_full_name: str,
        collector_url: str,
        project_id: int,
        branch: str | None = None,
    ) -> None:
        """Create or update Hook files in the repo."""
        target_branch = branch or self.default_branch
        files = self._build_hook_files(collector_url, project_id)
        for path, content in files.items():
            sha = self._get_file_sha(repo_full_name, path, target_branch)
            self._put_file(
                repo_full_name,
                path,
                content,
                "chore: update Cursor Hook files\n\nRe-injected by Sierac-tm platform.",
                target_branch,
                sha=sha,
            )
        log.info("Injected Hook files into GitHub repo %s", repo_full_name)


github_client = GitHubClient()
