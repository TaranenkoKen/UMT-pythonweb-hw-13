from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from config import settings

mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

fast_mail = FastMail(mail_config)


async def send_verification_email(email: str, token: str) -> None:
    """Send an email-verification link to the newly registered user.

    Args:
        email: Recipient's email address.
        token: Signed JWT that the user must click to verify their address.
    """
    verify_url = f"http://localhost:8000/auth/verify/{token}"
    html = f"""
    <p>Дякуємо за реєстрацію!</p>
    <p>Для підтвердження вашої електронної пошти натисніть посилання:</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>Посилання діє 24 години.</p>
    """
    message = MessageSchema(
        subject="Підтвердження email — Contacts App",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    await fast_mail.send_message(message)


async def send_password_reset_email(email: str, token: str) -> None:
    """Send a password-reset link to the user.

    Args:
        email: Recipient's email address.
        token: Signed JWT embedded in the reset URL.
    """
    reset_url = f"http://localhost:8000/auth/reset-password/{token}"
    html = f"""
    <p>Ви запросили скидання пароля.</p>
    <p>Натисніть посилання нижче, щоб встановити новий пароль:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>Посилання діє 1 годину. Якщо ви не робили цього запиту — просто ігноруйте цей лист.</p>
    """
    message = MessageSchema(
        subject="Скидання пароля — Contacts App",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    await fast_mail.send_message(message)
