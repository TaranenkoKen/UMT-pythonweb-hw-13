from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables / .env file.

    Attributes:
        DATABASE_URL: PostgreSQL connection string.
        SECRET_KEY: Secret key for JWT signing.
        ALGORITHM: JWT signing algorithm.
        ACCESS_TOKEN_EXPIRE_MINUTES: Lifetime of access tokens in minutes.
        REFRESH_TOKEN_EXPIRE_DAYS: Lifetime of refresh tokens in days.
        REDIS_URL: Redis connection URL for caching.
        MAIL_USERNAME: SMTP username.
        MAIL_PASSWORD: SMTP password.
        MAIL_FROM: Sender email address.
        MAIL_PORT: SMTP port.
        MAIL_SERVER: SMTP server hostname.
        MAIL_FROM_NAME: Display name for outgoing emails.
        CLOUDINARY_NAME: Cloudinary cloud name.
        CLOUDINARY_API_KEY: Cloudinary API key.
        CLOUDINARY_API_SECRET: Cloudinary API secret.
    """

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://localhost:6379"

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 465
    MAIL_SERVER: str
    MAIL_FROM_NAME: str = "Contacts App"

    CLOUDINARY_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
