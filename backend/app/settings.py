from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Advanced AI Demand Forecasting Enterprise API - Developed by Yogeshwaran K"
    app_version: str = "4.0.0"
    database_url: str = "sqlite:///./enterprise_forecasting.db"
    jwt_secret: str = "change-this-enterprise-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 1440
    rate_limit_requests: int = 180
    rate_limit_window_seconds: int = 60
    max_upload_mb: int = 25
    email_notifications_enabled: bool = False
    email_from: str = "alerts@forecast.local"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]


settings = Settings()

