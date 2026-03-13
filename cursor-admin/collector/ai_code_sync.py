"""
Sync AI Code Tracking API commits into ai_code_commits table.
Incremental sync by commit_ts; project_id matched via repo_name ↔ projects.git_repos.
"""

import logging
from datetime import datetime, timedelta, timezone

from cursor_api import get_ai_code_commits
from database import get_pool

log = logging.getLogger("ai_code_sync")


def _normalize_repo_slug(url_or_slug: str) -> str:
    """
    Extract 'org/repo' from URL or return as-is if already slug-like.
    Examples: https://gitlab.com/org/repo.git -> org/repo, git@github.com:org/repo.git -> org/repo.
    """
    s = (url_or_slug or "").strip().rstrip("/")
    if not s:
        return ""
    if "://" in s:
        # https://host/org/repo or .../org/repo.git
        parts = s.split("://", 1)[1].split("/")
        if len(parts) >= 2:
            slug = "/".join(parts[1:]).replace(".git", "")
            return slug.lower()
    if "@" in s and ":" in s:
        # git@host:org/repo.git
        slug = s.split(":", 1)[1].replace(".git", "")
        return slug.lower()
    return s.lower()


def match_project(repo_name: str, projects: list[dict]) -> int | None:
    """
    Match repo_name (e.g. 'org/repo-name') to a project by comparing to projects' git_repos.
    Returns project_id or None.
    """
    if not repo_name:
        return None
    repo_slug = _normalize_repo_slug(repo_name)
    for p in projects:
        for gr in p.get("git_repos") or []:
            if _normalize_repo_slug(gr) == repo_slug:
                return p["id"]
    return None


def _parse_commit_ts(value) -> datetime | None:
    """Parse API commitTs (ms or ISO string) to timezone-aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


async def sync_ai_code_commits() -> None:
    """
    1. Get max commit_ts from ai_code_commits as start (or 30d ago if empty).
    2. Fetch commits from API (start_date -> now) with pagination.
    3. For each commit: match project_id from repo_name; upsert into ai_code_commits.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT MAX(commit_ts) AS max_ts FROM ai_code_commits"
        )
        max_ts = row["max_ts"] if row and row["max_ts"] else None
        if max_ts is None:
            start_dt = datetime.now(timezone.utc) - timedelta(days=30)
        else:
            start_dt = max_ts if max_ts.tzinfo else max_ts.replace(tzinfo=timezone.utc)
        end_dt = datetime.now(timezone.utc)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")

        rows = await conn.fetch(
            "SELECT id, git_repos FROM projects WHERE status = 'active'"
        )
        projects = [{"id": r["id"], "git_repos": list(r["git_repos"] or [])} for r in rows]

    page = 1
    page_size = 1000
    total_upserted = 0
    etag: str | None = None

    try:
        while True:
            data = await get_ai_code_commits(
                start_date=start_date,
                end_date=end_date,
                page=page,
                page_size=page_size,
                etag=etag,
            )
            commits = data.get("commits") or []
            if not commits and not data.get("cached"):
                break
            if data.get("cached"):
                break

            async with pool.acquire() as conn:
                for c in commits:
                    commit_ts = _parse_commit_ts(c.get("commitTs"))
                    if commit_ts is None:
                        continue
                    repo_name = c.get("repoName") or ""
                    project_id = match_project(repo_name, projects)
                    await conn.execute(
                        """
                        INSERT INTO ai_code_commits (
                            commit_hash, user_id, user_email, repo_name, branch_name,
                            project_id, total_lines_added, total_lines_deleted,
                            tab_lines_added, tab_lines_deleted,
                            composer_lines_added, composer_lines_deleted,
                            non_ai_lines_added, non_ai_lines_deleted,
                            commit_message, commit_ts
                        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                        ON CONFLICT (commit_hash, user_email) DO UPDATE SET
                            user_id = EXCLUDED.user_id,
                            repo_name = EXCLUDED.repo_name,
                            branch_name = EXCLUDED.branch_name,
                            project_id = EXCLUDED.project_id,
                            total_lines_added = EXCLUDED.total_lines_added,
                            total_lines_deleted = EXCLUDED.total_lines_deleted,
                            tab_lines_added = EXCLUDED.tab_lines_added,
                            tab_lines_deleted = EXCLUDED.tab_lines_deleted,
                            composer_lines_added = EXCLUDED.composer_lines_added,
                            composer_lines_deleted = EXCLUDED.composer_lines_deleted,
                            non_ai_lines_added = EXCLUDED.non_ai_lines_added,
                            non_ai_lines_deleted = EXCLUDED.non_ai_lines_deleted,
                            commit_message = EXCLUDED.commit_message,
                            commit_ts = EXCLUDED.commit_ts,
                            synced_at = NOW()
                        """,
                        c.get("commitHash") or "",
                        c.get("userId"),
                        c.get("userEmail") or "",
                        repo_name,
                        c.get("branchName"),
                        project_id,
                        c.get("totalLinesAdded", 0) or 0,
                        c.get("totalLinesDeleted", 0) or 0,
                        c.get("tabLinesAdded", 0) or 0,
                        c.get("tabLinesDeleted", 0) or 0,
                        c.get("composerLinesAdded", 0) or 0,
                        c.get("composerLinesDeleted", 0) or 0,
                        c.get("nonAiLinesAdded", 0) or 0,
                        c.get("nonAiLinesDeleted", 0) or 0,
                        c.get("message"),
                        commit_ts,
                    )
                    total_upserted += 1

            pagination = data.get("pagination") or {}
            total_count = pagination.get("totalCount", 0)
            if not commits or len(commits) < page_size or (total_count and page * page_size >= total_count):
                break
            page += 1

        log.info("AI code sync: upserted %d commits (%s to %s)", total_upserted, start_date, end_date)
    except Exception as e:
        log.exception("AI code sync failed: %s", e)
        # Do not re-raise: other scheduled tasks (sync, alerts) must keep running
