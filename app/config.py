from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "IPS Appointment Mock"
    version: str = "0.3.0"

    ips_name: str = Field(default="IPS Demo", alias="IPS_NAME")
    ips_slug: str = Field(default="ips-demo", alias="IPS_SLUG")
    ips_code: str = Field(default="IPS-DEMO", alias="IPS_CODE")
    ips_nit: str = Field(default="900000000-0", alias="IPS_NIT")
    timezone: str = Field(default="America/Bogota", alias="TIMEZONE")
    port: int = Field(default=4011, alias="PORT")
    api_key: str = Field(default="dev-api-key", alias="API_KEY")
    db_path: str = Field(default="./data/ips.db", alias="DB_PATH")
    reset_db_on_startup: bool = Field(default=True, alias="RESET_DB_ON_STARTUP")


@lru_cache
def get_settings() -> Settings:
    return Settings()
