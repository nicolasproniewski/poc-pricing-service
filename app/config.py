from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    fred_api_key: str = ""
    coingecko_api_key: str = ""  # optional — blank = free tier
    btc_poll_interval_minutes: int = 60  # set to 0 to disable BTC polling

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
