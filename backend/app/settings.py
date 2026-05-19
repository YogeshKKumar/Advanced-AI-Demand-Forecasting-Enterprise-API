from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Advanced AI Demand Forecasting Enterprise API - Developed by Yogeshwaran K"
    app_version: str = "3.0.0"
    database_url: str = "sqlite:///./enterprise_forecasting.db"
    jwt_secret: str = "change-this-enterprise-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 1440
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ]


settings = Settings()
