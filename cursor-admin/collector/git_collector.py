"""
Git contribution collector: clone/fetch project repos, run git log + diff,
upsert into git_contributions. Runs as a scheduled job after sync.
"""

import asyncio
import hashlib
import logging
import os
from datetime import date, timedelta

from config import settings
from database import get_pool

log = logging.getLogger("git_collector")


def _repo_hash(repo_url: str) -> str:
    """Stable short hash for a repo URL (for directory name)."""
    return hashlib.sha256(repo_url.encode()).hexdigest()[:12]


async def _run_git(cwd: str, *args: str) -> tuple[int, str, str]:
    """Run git in repo dir; return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")


def _parse_numstat(text: str) -> tuple[int, int, int]:
    """Parse 'git show --numstat' output: sum insertions, deletions, file count."""
    lines_added, lines_removed, files_changed = 0, 0, 0
    for line in text.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            try:
                a, b = int(parts[0]) if parts[0] != "-" else 0, int(parts[1]) if parts[1] != "-" else 0
                lines_added += a
                lines_removed += b
                files_changed += 1
            except ValueError:
                continue
    return lines_added, lines_removed, files_changed


async def _collect_one_repo(project_id: int, repo_url: str, since_date: date) -> None:
    """
    Clone or fetch repo, scan commits since since_date, upsert into git_contributions.
    Single repo failure is logged and does not raise.
    """
    root = os.path.abspath(settings.git_repos_root)
    os.makedirs(root, exist_ok=True)
    repo_dir = os.path.join(root, str(project_id), _repo_hash(repo_url))
    os.makedirs(os.path.dirname(repo_dir), exist_ok=True)

    if not os.path.isdir(os.path.join(repo_dir, "refs")):
        code, out, err = await _run_git(os.path.dirname(repo_dir), "clone", "--bare", repo_url, os.path.basename(repo_dir))
        if code != 0:
            log.warning("git clone failed for project_id=%s url=%s: %s", project_id, repo_url, err.strip())
            return
        log.info("Cloned project_id=%s repo=%s", project_id, repo_url)
    else:
        code, out, err = await _run_git(repo_dir, "fetch", "--all")
        if code != 0:
            log.warning("git fetch failed for project_id=%s url=%s: %s", project_id, repo_url, err.strip())
            return

    since_str = since_date.isoformat()
    code, log_out, err = await _run_git(repo_dir, "log", f"--since={since_str}", "--format=%ae|%ad|%H", "--date=short")
    if code != 0:
        log.warning("git log failed for project_id=%s: %s", project_id, err.strip())
        return

    # Parse commits: author_email, commit_date, hash
    commits: list[tuple[str, str, str]] = []
    for line in log_out.strip().splitlines():
        if "|" in line:
            parts = line.strip().split("|")
            if len(parts) >= 3:
                author_email, commit_date_str, commit_hash = parts[0].strip(), parts[1].strip(), parts[2].strip()
                if author_email and commit_date_str and commit_hash:
                    commits.append((author_email, commit_date_str, commit_hash))

    # Aggregate by (author_email, commit_date)
    agg: dict[tuple[str, str], list[str]] = {}
    for author_email, commit_date_str, commit_hash in commits:
        key = (author_email, commit_date_str)
        agg.setdefault(key, []).append(commit_hash)

    pool = await get_pool()
    for (author_email, commit_date_str), hashes in agg.items():
        total_added, total_removed, total_files = 0, 0, 0
        for h in hashes:
            code2, numstat_out, _ = await _run_git(repo_dir, "show", "--numstat", "--format=", h)
            if code2 == 0:
                a, r, f = _parse_numstat(numstat_out)
                total_added += a
                total_removed += r
                total_files += f
        try:
            commit_date = date.fromisoformat(commit_date_str)
        except ValueError:
            continue
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO git_contributions
                    (project_id, author_email, commit_date, commit_count, lines_added, lines_removed, files_changed)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (project_id, author_email, commit_date) DO UPDATE SET
                    commit_count   = git_contributions.commit_count + EXCLUDED.commit_count,
                    lines_added    = git_contributions.lines_added + EXCLUDED.lines_added,
                    lines_removed  = git_contributions.lines_removed + EXCLUDED.lines_removed,
                    files_changed  = git_contributions.files_changed + EXCLUDED.files_changed
                """,
                project_id,
                author_email,
                commit_date,
                len(hashes),
                total_added,
                total_removed,
                total_files,
            )
    if commits:
        log.info("Collected project_id=%s repo=%s commits=%d", project_id, repo_url, len(commits))


async def run_git_collect() -> None:
    """
    For each active project with git_repos, clone/fetch and scan commits in the last
    git_collect_days, upsert into git_contributions. Per-repo errors are logged only.
    """
    since_date = date.today() - timedelta(days=settings.git_collect_days)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, git_repos FROM projects WHERE status = 'active' AND git_repos IS NOT NULL AND array_length(git_repos, 1) > 0"
        )
    for row in rows:
        project_id = row["id"]
        repos = row["git_repos"] or []
        for repo_url in repos:
            repo_url = (repo_url or "").strip()
            if not repo_url:
                continue
            try:
                await _collect_one_repo(project_id, repo_url, since_date)
            except Exception as e:
                log.exception("Git collect failed project_id=%s url=%s: %s", project_id, repo_url, e)
