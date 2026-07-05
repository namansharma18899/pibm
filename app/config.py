from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite:///./pibm.db"

    model_config = {"env_file": ".env"}


settings = Settings()
