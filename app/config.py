from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "EPS Appointment Mock"
    version: str = "0.2.0"

    eps_name: str = Field(default="EPS Demo", alias="EPS_NAME")
    eps_slug: str = Field(default="eps-demo", alias="EPS_SLUG")
    eps_code: str = Field(default="EPS-DEMO", alias="EPS_CODE")
    timezone: str = Field(default="America/Bogota", alias="TIMEZONE")
    port: int = Field(default=4011, alias="PORT")
    api_key: str = Field(default="dev-api-key", alias="API_KEY")
    db_path: str = Field(default="./data/eps.db", alias="DB_PATH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
