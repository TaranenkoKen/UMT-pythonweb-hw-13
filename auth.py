from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt as _bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from config import settings
import crud
from cache import get_cached_user, cache_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Token type constants used in JWT payloads.
_TYPE_ACCESS = "access"
_TYPE_REFRESH = "refresh"
_TYPE_EMAIL_VERIFY = "email_verification"
_TYPE_PASSWORD_RESET = "password_reset"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check that a plain-text password matches its bcrypt hash.

    Args:
        plain_password: The raw password supplied by the user.
        hashed_password: The stored bcrypt hash.

    Returns:
        ``True`` if the password matches, otherwise ``False``.
    """
    return _bcrypt.checkpw(plain_password[:72].encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    """Hash a plain-text password with bcrypt.

    Args:
        password: The raw password to hash (max 72 bytes used by bcrypt).

    Returns:
        A bcrypt hash string.
    """
    return _bcrypt.hashpw(password[:72].encode(), _bcrypt.gensalt()).decode()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token.

    Args:
        data: Claims to embed in the token (must include ``"sub"``).
        expires_delta: Custom lifetime; defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        An encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": _TYPE_ACCESS})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT refresh token with a longer lifetime.

    Args:
        data: Claims to embed (must include ``"sub"``).
        expires_delta: Custom lifetime; defaults to ``REFRESH_TOKEN_EXPIRE_DAYS``.

    Returns:
        An encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": _TYPE_REFRESH})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_refresh_token(token: str) -> Optional[str]:
    """Decode a refresh token and return the subject (email).

    Args:
        token: The encoded refresh JWT.

    Returns:
        The email from the ``"sub"`` claim, or ``None`` if the token is invalid.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != _TYPE_REFRESH:
            return None
        return payload.get("sub")
    except JWTError:
        return None


def create_email_token(email: str) -> str:
    """Create a short-lived JWT for email verification.

    Args:
        email: The email address to embed as the ``"sub"`` claim.

    Returns:
        An encoded JWT string valid for 24 hours.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {"sub": email, "type": _TYPE_EMAIL_VERIFY, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_email_token(token: str) -> Optional[str]:
    """Decode an email-verification token.

    Args:
        token: The encoded verification JWT.

    Returns:
        The email address, or ``None`` if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != _TYPE_EMAIL_VERIFY:
            return None
        return payload.get("sub")
    except JWTError:
        return None


def create_password_reset_token(email: str) -> str:
    """Create a short-lived JWT for password reset.

    Args:
        email: The email address that requested the reset.

    Returns:
        An encoded JWT string valid for 1 hour.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": email, "type": _TYPE_PASSWORD_RESET, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_password_reset_token(token: str) -> Optional[str]:
    """Decode a password-reset token.

    Args:
        token: The encoded password-reset JWT.

    Returns:
        The email address, or ``None`` if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != _TYPE_PASSWORD_RESET:
            return None
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Resolve the currently authenticated user, using Redis cache when available.

    The function first tries to load the user from Redis to avoid a database
    round-trip on every request.  On a cache miss the user is fetched from the
    database and then stored in Redis for subsequent requests.

    Args:
        token: Bearer JWT extracted by ``OAuth2PasswordBearer``.
        db: SQLAlchemy database session injected by FastAPI.

    Returns:
        The authenticated ``models.User`` instance.

    Raises:
        HTTPException: 401 if the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") not in (_TYPE_ACCESS, None):
            raise credentials_exception
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Try Redis cache first.
    cached = await get_cached_user(email)
    if cached:
        user = crud.get_user_by_email(db, email)
        if user is None:
            raise credentials_exception
        return user

    user = crud.get_user_by_email(db, email)
    if user is None:
        raise credentials_exception

    user_data = {
        "id": user.id,
        "email": user.email,
        "is_verified": user.is_verified,
        "role": user.role.value,
    }
    await cache_user(email, user_data)
    return user
