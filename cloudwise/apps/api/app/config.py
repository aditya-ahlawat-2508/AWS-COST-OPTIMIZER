import os


class Settings:
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://localhost/cloudwise"
    )
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expiry_seconds: int = 60 * 60 * 12  # 12 hours


settings = Settings()
