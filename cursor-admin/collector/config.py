from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 数据库
    database_url: str = "postgresql+asyncpg://cursor:cursor@db:5432/cursor_admin"

    # Cursor Admin API（需 Team/Enterprise 管理员在 dashboard 创建的 Admin API Key）
    cursor_api_token: str = ""
    cursor_api_url: str = "https://api.cursor.com"

    def get_cursor_token(self) -> str:
        """返回去除首尾空白与 CRLF 的 token，避免 .env 导致 401。"""
        return (self.cursor_api_token or "").strip().replace("\r", "").replace("\n", "")

    # 同步间隔（分钟）
    sync_interval_minutes: int = 60

    # 告警
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_ssl: bool = True

    # Webhook 默认（可选，如企业微信/钉钉）
    default_webhook_url: str = ""

    # 服务端口
    port: int = 8000

    # 内部 API 密钥（管理端调用采集服务时校验）
    internal_api_key: str = "change-me-in-production"

    # GitLab（立项时自动创建仓库、注入 Hook；不配置则仅支持手动关联已有仓库）
    gitlab_url: str = ""
    gitlab_token: str = ""
    gitlab_group_id: int = 0
    gitlab_default_branch: str = "main"
    gitlab_visibility: str = "private"


settings = Settings()
