from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量读取的应用配置。"""

    app_name: str = "租安AI API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    frontend_origins: str = "http://localhost:5173"
    # 保持项目首次启动可用；生产环境必须通过环境变量配置 MySQL URL。
    database_url: str = "sqlite:///./rent_safe_ai.db"
    auto_create_tables: bool = True
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20
    ai_provider: str = "mock"
    llm_api_base: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = 45
    dify_api_base: str = ""
    dify_api_key: str = ""
    dify_workflow_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def is_demo_mode(self) -> bool:
        return self.ai_provider.lower() == "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
