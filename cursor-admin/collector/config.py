from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 数据库
    database_url: str = "postgresql+asyncpg://cursor:cursor@db:5432/cursor_admin"

    # Cursor Admin API
    cursor_api_token: str = ""
    cursor_api_url: str = "https://api.cursor.com"

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


settings = Settings()
