from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import models, schemas, crud, auth
from database import engine, get_db
from email_service import send_verification_email, send_password_reset_email
from cache import invalidate_user_cache
import cloudinary
import cloudinary.uploader
from config import settings

models.Base.metadata.create_all(bind=engine)

cloudinary.config(
    cloud_name=settings.CLOUDINARY_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Contacts API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post(
    "/auth/signup",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
async def signup(body: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user and send an email-verification link.

    Args:
        body: Registration payload containing email and password.
        db: Injected database session.

    Returns:
        The newly created user object.

    Raises:
        HTTPException: 409 if the email is already registered.
    """
    if crud.get_user_by_email(db, body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    user = crud.create_user(db, body)
    token = auth.create_email_token(user.email)
    try:
        await send_verification_email(user.email, token)
    except Exception as e:
        print(f"[EMAIL] Could not send verification email: {e}")
        print(f"[EMAIL] Verification URL: http://localhost:8000/auth/verify/{token}")
    return user


@app.post("/auth/login", response_model=schemas.TokenModel, tags=["auth"])
async def login(body: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate a user and return a pair of JWT tokens.

    Args:
        body: OAuth2 form with ``username`` (email) and ``password``.
        db: Injected database session.

    Returns:
        A :class:`schemas.TokenModel` with ``access_token`` and ``refresh_token``.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user = crud.get_user_by_email(db, body.username)
    if not user or not auth.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    access_token = auth.create_access_token(data={"sub": user.email})
    refresh_token = auth.create_refresh_token(data={"sub": user.email})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@app.post("/auth/refresh", response_model=schemas.TokenModel, tags=["auth"])
async def refresh_tokens(refresh_token: str, db: Session = Depends(get_db)):
    """Issue a new access/refresh token pair from a valid refresh token.

    Args:
        refresh_token: The JWT refresh token from a previous login.
        db: Injected database session.

    Returns:
        A new :class:`schemas.TokenModel`.

    Raises:
        HTTPException: 401 if the refresh token is invalid or the user does not exist.
    """
    email = auth.decode_refresh_token(refresh_token)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    new_access = auth.create_access_token(data={"sub": email})
    new_refresh = auth.create_refresh_token(data={"sub": email})
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


@app.get("/auth/verify/{token}", response_model=schemas.UserResponse, tags=["auth"])
def verify_email(token: str, db: Session = Depends(get_db)):
    """Confirm a user's email address using the token sent during registration.

    Args:
        token: The signed verification JWT from the email link.
        db: Injected database session.

    Returns:
        The verified user object.

    Raises:
        HTTPException: 400 for an invalid/expired token, 404 if user not found.
    """
    email = auth.decode_email_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")
    user = crud.verify_user(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.post("/auth/request-password-reset", status_code=status.HTTP_200_OK, tags=["auth"])
async def request_password_reset(body: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    """Send a password-reset link to the given email address.

    The response is always 200 to avoid leaking whether the email exists.

    Args:
        body: Payload containing the ``email`` to reset.
        db: Injected database session.

    Returns:
        A confirmation message dict.
    """
    user = crud.get_user_by_email(db, body.email)
    if user:
        token = auth.create_password_reset_token(user.email)
        try:
            await send_password_reset_email(user.email, token)
        except Exception as e:
            print(f"[EMAIL] Could not send password reset email: {e}")
            print(f"[EMAIL] Reset URL: http://localhost:8000/auth/reset-password/{token}")
    return {"message": "If this email exists, a reset link has been sent."}


@app.post("/auth/reset-password", status_code=status.HTTP_200_OK, tags=["auth"])
async def reset_password(body: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    """Set a new password using a valid password-reset token.

    Args:
        body: Payload with the reset ``token`` and ``new_password``.
        db: Injected database session.

    Returns:
        A confirmation message dict.

    Raises:
        HTTPException: 400 if the token is invalid or expired, 404 if user not found.
    """
    email = auth.decode_password_reset_token(body.token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user = crud.reset_user_password(db, email, body.new_password)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await invalidate_user_cache(email)
    return {"message": "Password updated successfully."}


# ---------------------------------------------------------------------------
# User routes
# ---------------------------------------------------------------------------

@app.get("/users/me", response_model=schemas.UserResponse, tags=["users"])
@limiter.limit("10/minute")
async def get_me(request: Request, current_user: models.User = Depends(auth.get_current_user)):
    """Return the profile of the currently authenticated user.

    Args:
        request: The incoming HTTP request (required by the rate limiter).
        current_user: Resolved from the Bearer token via dependency injection.

    Returns:
        The current :class:`models.User`.
    """
    return current_user


@app.patch("/users/avatar", response_model=schemas.UserResponse, tags=["users"])
async def update_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a new avatar image for the current user (admin only).

    Only users with the ``admin`` role may change their avatar via this endpoint.

    Args:
        file: The image file to upload.
        current_user: The authenticated user (must be an admin).
        db: Injected database session.

    Returns:
        The updated :class:`models.User`.

    Raises:
        HTTPException: 403 if the user is not an admin.
    """
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change their avatar")
    result = cloudinary.uploader.upload(
        file.file,
        public_id=f"avatars/{current_user.email}",
        overwrite=True,
    )
    url = result["secure_url"]
    updated = crud.update_user_avatar(db, current_user, url)
    await invalidate_user_cache(current_user.email)
    return updated


# ---------------------------------------------------------------------------
# Contacts routes
# ---------------------------------------------------------------------------

@app.post(
    "/contacts/",
    response_model=schemas.ContactResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["contacts"],
)
def create(
    contact: schemas.ContactBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Create a new contact for the authenticated user.

    Args:
        contact: Contact data payload.
        db: Injected database session.
        current_user: The authenticated owner.

    Returns:
        The newly created :class:`models.Contact`.
    """
    return crud.create_contact(db, contact, current_user)


@app.get("/contacts/", response_model=List[schemas.ContactResponse], tags=["contacts"])
def read_all(
    name: str = None,
    last_name: str = None,
    email: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Return all contacts owned by the authenticated user with optional search filters.

    Args:
        name: Optional partial ``first_name`` filter.
        last_name: Optional partial ``last_name`` filter.
        email: Optional partial email filter.
        db: Injected database session.
        current_user: The authenticated owner.

    Returns:
        List of matching :class:`models.Contact` instances.
    """
    return crud.get_contacts(db, current_user, name, last_name, email)


@app.get("/contacts/birthdays", response_model=List[schemas.ContactResponse], tags=["contacts"])
def birthdays(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Return contacts whose birthday falls within the next 7 days.

    Args:
        db: Injected database session.
        current_user: The authenticated owner.

    Returns:
        List of :class:`models.Contact` instances with upcoming birthdays.
    """
    return crud.get_upcoming_birthdays(db, current_user)


@app.get("/contacts/{contact_id}", response_model=schemas.ContactResponse, tags=["contacts"])
def read_one(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Return a single contact by ID (must be owned by the authenticated user).

    Args:
        contact_id: Primary key of the contact.
        db: Injected database session.
        current_user: The authenticated owner.

    Returns:
        The :class:`models.Contact` instance.

    Raises:
        HTTPException: 404 if the contact does not exist or belongs to another user.
    """
    contact = crud.get_contact(db, contact_id, current_user)
    if not contact:
        raise HTTPException(status_code=404, detail="Not found")
    return contact


@app.put("/contacts/{contact_id}", response_model=schemas.ContactResponse, tags=["contacts"])
def update(
    contact_id: int,
    body: schemas.ContactBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Update an existing contact owned by the authenticated user.

    Args:
        contact_id: Primary key of the contact to update.
        body: New contact data.
        db: Injected database session.
        current_user: The authenticated owner.

    Returns:
        The updated :class:`models.Contact`.

    Raises:
        HTTPException: 404 if the contact does not exist.
    """
    contact = crud.update_contact(db, contact_id, body, current_user)
    if not contact:
        raise HTTPException(status_code=404, detail="Not found")
    return contact


@app.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["contacts"])
def delete(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Delete a contact owned by the authenticated user.

    Args:
        contact_id: Primary key of the contact to delete.
        db: Injected database session.
        current_user: The authenticated owner.

    Raises:
        HTTPException: 404 if the contact does not exist.
    """
    contact = crud.delete_contact(db, contact_id, current_user)
    if not contact:
        raise HTTPException(status_code=404, detail="Not found")
    return None
