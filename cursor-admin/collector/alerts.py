"""
告警检测与通知
- 每次同步后运行
- 支持邮件（SMTP）和 Webhook（企业微信/钉钉/自定义）
"""

import json
import logging
import smtplib
import ssl
from datetime import date, timedelta
from email.mime.text import MIMEText

import httpx
from config import settings
from database import get_pool

log = logging.getLogger("alerts")


# ─── 通知渠道 ─────────────────────────────────────────────────────────────────


async def notify_email(address: str, subject: str, body: str):
    if not settings.smtp_host or not settings.smtp_user:
        log.warning("SMTP not configured, skipping email alert")
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = address
    try:
        if settings.smtp_use_ssl:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ctx) as s:
                s.login(settings.smtp_user, settings.smtp_password)
                s.sendmail(msg["From"], [address], msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
                s.starttls()
                s.login(settings.smtp_user, settings.smtp_password)
                s.sendmail(msg["From"], [address], msg.as_string())
        log.info("Email alert sent to %s", address)
    except Exception as e:
        log.error("Email alert failed: %s", e)


async def notify_webhook(url: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)
        log.info("Webhook alert sent to %s", url)
    except Exception as e:
        log.error("Webhook alert failed: %s", e)


async def dispatch_alert(rule: dict, metric_value: float, detail: dict):
    channels = rule.get("notify_channels") or []
    if isinstance(channels, str):
        channels = json.loads(channels)

    subject = f"[Cursor Admin] 告警：{rule['name']}"
    body = (
        f"规则：{rule['name']}\n"
        f"指标：{rule['metric']}\n"
        f"当前值：{metric_value}\n"
        f"阈值：{rule['threshold']}\n"
        f"详情：{json.dumps(detail, ensure_ascii=False)}"
    )

    for ch in channels:
        ch_type = ch.get("type", "")
        if ch_type == "email":
            await notify_email(ch.get("address", ""), subject, body)
        elif ch_type == "webhook":
            await notify_webhook(
                ch.get("url", ""),
                {
                    "msgtype": "text",
                    "text": {"content": body},
                    "rule": rule["name"],
                    "metric": rule["metric"],
                    "value": metric_value,
                    "threshold": rule["threshold"],
                    "detail": detail,
                },
            )

    # 如果没有配置渠道但有全局 webhook，也发一次
    if not channels and settings.default_webhook_url:
        await notify_webhook(
            settings.default_webhook_url,
            {
                "msgtype": "text",
                "text": {"content": body},
            },
        )


# ─── 告警检测 ─────────────────────────────────────────────────────────────────


async def check_alerts():
    pool = await get_pool()
    today = date.today()
    yesterday = today - timedelta(days=1)

    async with pool.acquire() as conn:
        rules = await conn.fetch("SELECT * FROM alert_rules WHERE enabled = TRUE")

        for rule in rules:
            rule = dict(rule)
            metric = rule["metric"]
            scope = rule["scope"]
            threshold = float(rule["threshold"])

            # 已在冷却期内（同一规则 1 小时内不重复告警）
            last = await conn.fetchrow(
                "SELECT triggered_at FROM alert_events WHERE rule_id=$1 ORDER BY triggered_at DESC LIMIT 1",
                rule["id"],
            )
            if last:
                from datetime import datetime, timezone

                delta = datetime.now(timezone.utc) - last["triggered_at"]
                if delta.total_seconds() < 3600:
                    continue

            value = None
            detail = {}

            if metric == "daily_agent_requests":
                if scope == "user" and rule.get("target_email"):
                    row = await conn.fetchrow(
                        "SELECT agent_requests FROM daily_usage WHERE email=$1 AND day=$2",
                        rule["target_email"],
                        yesterday,
                    )
                    value = float(row["agent_requests"]) if row else 0.0
                    detail = {"email": rule["target_email"], "day": str(yesterday)}
                elif scope == "team":
                    row = await conn.fetchrow(
                        "SELECT COALESCE(SUM(agent_requests),0) AS total FROM daily_usage WHERE day=$1",
                        yesterday,
                    )
                    value = float(row["total"]) if row else 0.0
                    detail = {"day": str(yesterday)}

            elif metric == "daily_spend_cents":
                if scope == "user" and rule.get("target_email"):
                    row = await conn.fetchrow(
                        "SELECT spend_cents FROM spend_snapshots WHERE email=$1 ORDER BY billing_cycle_start DESC LIMIT 1",
                        rule["target_email"],
                    )
                    value = float(row["spend_cents"]) if row else 0.0
                    detail = {"email": rule["target_email"]}
                elif scope == "team":
                    row = await conn.fetchrow(
                        "SELECT COALESCE(SUM(spend_cents),0) AS total FROM spend_snapshots WHERE billing_cycle_start=(SELECT MAX(billing_cycle_start) FROM spend_snapshots)"
                    )
                    value = float(row["total"]) if row else 0.0

            elif metric == "monthly_spend_cents":
                if scope == "user" and rule.get("target_email"):
                    row = await conn.fetchrow(
                        "SELECT spend_cents FROM spend_snapshots WHERE email=$1 ORDER BY billing_cycle_start DESC LIMIT 1",
                        rule["target_email"],
                    )
                    value = float(row["spend_cents"]) if row else 0.0
                    detail = {"email": rule["target_email"]}

            if value is not None and value >= threshold:
                log.warning(
                    "Alert triggered: rule=%s metric=%s value=%s threshold=%s",
                    rule["name"],
                    metric,
                    value,
                    threshold,
                )
                await dispatch_alert(rule, value, detail)
                await conn.execute(
                    "INSERT INTO alert_events (rule_id, metric_value, threshold, detail) VALUES ($1,$2,$3,$4)",
                    rule["id"],
                    value,
                    threshold,
                    json.dumps(detail),
                )
