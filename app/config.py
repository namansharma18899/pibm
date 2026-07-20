from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_client_id: str = ""
    google_client_secret: str = ""
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite:///./pibm.db"
    gemini_api_key: str = ""
    max_video_size_mb: int = 50
    monthly_credits: int = 100
    daily_video_limit: int = 5
    video_retention_days: int = 15
    mock_ai: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
