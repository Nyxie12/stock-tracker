from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    finnhub_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./stocktracker.db"
    cors_origins: str = "http://localhost:5173"
    tick_throttle_ms: int = 500
    debug: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
