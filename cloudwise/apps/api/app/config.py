import os


class Settings:
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://localhost/cloudwise"
    )


settings = Settings()
