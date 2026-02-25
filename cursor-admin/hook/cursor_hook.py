#!/usr/bin/env python3
"""
Cursor 极简 Hook 脚本
- 监听 stop 事件：上报会话结束 + workspace_roots + 时长
- 监听 beforeSubmitPrompt 事件：记录会话开始时间到本地（不上报）
每次 Agent 会话只产生 1 条上报，粗颗粒度，极低开销。

部署位置：~/.cursor/hooks/cursor_hook.py
配置文件：~/.cursor/hooks/hook_config.json
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import hashlib
import platform

# ─── 配置加载 ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "hook_config.json")
    defaults = {
        "collector_url": "http://localhost:8000",
        "user_email": "",          # 若为空则自动从环境变量/系统用户推断
        "machine_id": "",          # 若为空则自动生成（基于主机名哈希）
        "timeout_seconds": 5,
        "state_dir": os.path.join(os.path.expanduser("~"), ".cursor", "hooks", ".state"),
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            defaults.update(user_cfg)
        except Exception:
            pass
    return defaults


def get_machine_id(cfg: dict) -> str:
    if cfg.get("machine_id"):
        return cfg["machine_id"]
    raw = platform.node() + platform.machine()
    return "m-" + hashlib.md5(raw.encode()).hexdigest()[:12]


def get_user_email(cfg: dict) -> str:
    if cfg.get("user_email"):
        return cfg["user_email"]
    # 尝试从环境变量读取（部署时可通过 MDM/GPO 注入）
    for env_key in ("CURSOR_USER_EMAIL", "GIT_AUTHOR_EMAIL", "EMAIL"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    # 最后回退到系统用户名（不含域名）
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))

# ─── 本地状态（会话开始时间） ─────────────────────────────────────────────────

def ensure_state_dir(state_dir: str):
    os.makedirs(state_dir, exist_ok=True)


def state_file(state_dir: str, conversation_id: str) -> str:
    safe = conversation_id.replace("/", "_").replace("\\", "_")
    return os.path.join(state_dir, f"{safe}.json")


def save_session_start(state_dir: str, conversation_id: str, workspace_roots: list, ts: float):
    ensure_state_dir(state_dir)
    path = state_file(state_dir, conversation_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"started_at": ts, "workspace_roots": workspace_roots}, f)


def load_session_start(state_dir: str, conversation_id: str) -> dict | None:
    path = state_file(state_dir, conversation_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def delete_session_start(state_dir: str, conversation_id: str):
    path = state_file(state_dir, conversation_id)
    try:
        os.remove(path)
    except Exception:
        pass

# ─── 上报 ─────────────────────────────────────────────────────────────────────

def post_session(collector_url: str, payload: dict, timeout: int):
    url = collector_url.rstrip("/") + "/api/sessions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            pass
    except Exception:
        # 上报失败静默处理，不影响 Cursor 正常工作
        pass

# ─── 主逻辑 ───────────────────────────────────────────────────────────────────

def main():
    cfg = load_config()
    state_dir = cfg["state_dir"]
    user_email = get_user_email(cfg)
    machine_id = get_machine_id(cfg)
    collector_url = cfg["collector_url"]
    timeout = int(cfg.get("timeout_seconds", 5))

    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
    except Exception:
        # 无法解析 payload 时直接允许继续
        print(json.dumps({"continue": True}))
        return

    event_name = event.get("hook_event_name", "")
    conversation_id = event.get("conversation_id", "")
    workspace_roots = event.get("workspace_roots", [])
    now = time.time()

    if event_name == "beforeSubmitPrompt":
        # 记录会话开始时间到本地，不上报
        if conversation_id:
            save_session_start(state_dir, conversation_id, workspace_roots, now)
        print(json.dumps({"continue": True}))
        return

    if event_name == "stop":
        started_info = None
        duration_seconds = None
        if conversation_id:
            started_info = load_session_start(state_dir, conversation_id)
            if started_info:
                duration_seconds = int(now - started_info["started_at"])
                # workspace_roots 优先用 stop 时的，若为空则用 start 时记录的
                if not workspace_roots:
                    workspace_roots = started_info.get("workspace_roots", [])
                delete_session_start(state_dir, conversation_id)

        payload = {
            "event": "session_end",
            "conversation_id": conversation_id,
            "user_email": user_email,
            "machine_id": machine_id,
            "workspace_roots": workspace_roots,
            "ended_at": int(now),
            "duration_seconds": duration_seconds,
        }
        post_session(collector_url, payload, timeout)
        print(json.dumps({"continue": True}))
        return

    # 其他事件一律放行
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
