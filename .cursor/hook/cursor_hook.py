#!/usr/bin/env python3
"""
Sierac-tm Cursor Hook
- beforeSubmitPrompt: whitelist check (block if not in approved project) + record session start
- stop: report session end with project_id to collector

Whitelist is cached locally (whitelist_cache.json, 5-min TTL) to avoid
a network round-trip on every keystroke.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import hashlib
import platform

# ─── Config ──────────────────────────────────────────────────────────────────

def load_config() -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "hook_config.json")
    defaults = {
        "collector_url": "http://localhost:8000",
        "user_email": "",
        "machine_id": "",
        "timeout_seconds": 5,
        "whitelist_ttl_seconds": 300,
        "state_dir": os.path.join(script_dir, ".state"),
        "whitelist_enabled": True,
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    if not defaults.get("state_dir"):
        defaults["state_dir"] = os.path.join(script_dir, ".state")
    return defaults


def get_machine_id(cfg: dict) -> str:
    if cfg.get("machine_id"):
        return cfg["machine_id"]
    return "m-" + hashlib.md5((platform.node() + platform.machine()).encode()).hexdigest()[:12]


def get_user_email(cfg: dict) -> str:
    if cfg.get("user_email"):
        return cfg["user_email"]
    for env_key in ("CURSOR_USER_EMAIL", "GIT_AUTHOR_EMAIL", "EMAIL"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))

# ─── Local state (session start time + matched project) ──────────────────────

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def state_path(state_dir: str, conversation_id: str) -> str:
    safe = conversation_id.replace("/", "_").replace("\\", "_")
    return os.path.join(state_dir, f"{safe}.json")


def save_state(state_dir: str, conversation_id: str, data: dict):
    ensure_dir(state_dir)
    with open(state_path(state_dir, conversation_id), "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_state(state_dir: str, conversation_id: str) -> dict | None:
    p = state_path(state_dir, conversation_id)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def delete_state(state_dir: str, conversation_id: str):
    try:
        os.remove(state_path(state_dir, conversation_id))
    except Exception:
        pass

# ─── Whitelist cache ──────────────────────────────────────────────────────────

def whitelist_cache_path(state_dir: str) -> str:
    return os.path.join(state_dir, "whitelist_cache.json")


def load_whitelist_cache(state_dir: str, ttl: int) -> list | None:
    """Return cached rules if fresh, else None."""
    p = whitelist_cache_path(state_dir)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if time.time() - cached.get("fetched_at", 0) < ttl:
            return cached.get("rules", [])
    except Exception:
        pass
    return None


def fetch_whitelist(collector_url: str, timeout: int) -> list | None:
    """Fetch whitelist from collector. Returns list of rule dicts or None on error."""
    url = collector_url.rstrip("/") + "/api/projects/whitelist"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("rules", [])
    except Exception:
        return None


def save_whitelist_cache(state_dir: str, rules: list):
    ensure_dir(state_dir)
    with open(whitelist_cache_path(state_dir), "w", encoding="utf-8") as f:
        json.dump({"fetched_at": time.time(), "rules": rules}, f)


def get_whitelist(cfg: dict) -> list | None:
    """Get whitelist rules: cache first, then network, then None (fail-open)."""
    state_dir = cfg["state_dir"]
    ttl = int(cfg.get("whitelist_ttl_seconds", 300))
    rules = load_whitelist_cache(state_dir, ttl)
    if rules is not None:
        return rules
    rules = fetch_whitelist(cfg["collector_url"], int(cfg.get("timeout_seconds", 5)))
    if rules is not None:
        save_whitelist_cache(state_dir, rules)
    return rules

# ─── Whitelist matching ───────────────────────────────────────────────────────

def match_whitelist(workspace_roots: list[str], user_email: str, rules: list) -> dict | None:
    """
    Return the first matching rule dict, or None if no match.
    Matching logic:
    - workspace root must start with one of rule's workspace_rules (case-insensitive on Windows)
    - if rule has member_emails, user_email must be in the list
    """
    is_windows = sys.platform == "win32"

    for rule in rules:
        rule_paths: list[str] = rule.get("workspace_rules", [])
        member_emails: list[str] = rule.get("member_emails", [])

        for root in workspace_roots:
            for rule_path in rule_paths:
                rp = (rule_path or "").strip().rstrip("。，,; \t\n\r")  # avoid UI typo (e.g. trailing 。)
                if not rp:
                    continue
                if is_windows:
                    matched = root.lower().startswith(rp.lower())
                else:
                    matched = root.startswith(rp)

                if matched:
                    if member_emails and user_email.lower() not in [e.lower() for e in member_emails]:
                        continue
                    return rule

    return None

# ─── Report session ───────────────────────────────────────────────────────────

def post_session(collector_url: str, payload: dict, timeout: int):
    url = collector_url.rstrip("/") + "/api/sessions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            pass
    except Exception:
        pass

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    cfg = load_config()
    state_dir = cfg["state_dir"]
    user_email = get_user_email(cfg)
    machine_id = get_machine_id(cfg)
    collector_url = cfg["collector_url"]
    timeout = int(cfg.get("timeout_seconds", 5))
    whitelist_enabled = cfg.get("whitelist_enabled", True)

    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    event_name = event.get("hook_event_name", "")
    conversation_id = event.get("conversation_id", "")
    workspace_roots = event.get("workspace_roots", [])
    now = time.time()

    # ── beforeSubmitPrompt ────────────────────────────────────────────────────
    if event_name == "beforeSubmitPrompt":
        matched_project_id = None

        if whitelist_enabled:
            rules = get_whitelist(cfg)

            if rules is None:
                # Network error → fail-open: let the user work, log warning
                pass
            else:
                matched = match_whitelist(workspace_roots, user_email, rules)
                if matched is None:
                    print(json.dumps({
                        "continue": False,
                        "message": (
                            "⛔ 当前工作目录未在公司项目白名单中。\n"
                            "请联系管理员在 Sierac 平台完成项目立项后再使用企业 Cursor。\n"
                            f"当前目录: {workspace_roots}"
                        ),
                    }))
                    return
                matched_project_id = matched.get("project_id")

        if conversation_id:
            save_state(state_dir, conversation_id, {
                "started_at": now,
                "workspace_roots": workspace_roots,
                "project_id": matched_project_id,
            })

        print(json.dumps({"continue": True}))
        return

    # ── stop ──────────────────────────────────────────────────────────────────
    if event_name == "stop":
        duration_seconds = None
        project_id = None

        if conversation_id:
            saved = load_state(state_dir, conversation_id)
            if saved:
                duration_seconds = int(now - saved["started_at"])
                project_id = saved.get("project_id")
                if not workspace_roots:
                    workspace_roots = saved.get("workspace_roots", [])
                delete_state(state_dir, conversation_id)

        payload = {
            "event": "session_end",
            "conversation_id": conversation_id,
            "user_email": user_email,
            "machine_id": machine_id,
            "workspace_roots": workspace_roots,
            "ended_at": int(now),
            "duration_seconds": duration_seconds,
            "project_id": project_id,
        }
        post_session(collector_url, payload, timeout)
        print(json.dumps({"continue": True}))
        return

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
