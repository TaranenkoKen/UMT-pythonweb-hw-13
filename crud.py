from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models, schemas, auth


def create_contact(db: Session, contact: schemas.ContactBase, user: models.User) -> models.Contact:
    """Create a new contact belonging to the given user.

    Args:
        db: Active database session.
        contact: Validated contact payload.
        user: The owner of the new contact.

    Returns:
        The newly created :class:`models.Contact` instance.
    """
    db_contact = models.Contact(**contact.model_dump(), owner_id=user.id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def get_contacts(
    db: Session,
    user: models.User,
    name: str = None,
    last_name: str = None,
    email: str = None,
) -> list[models.Contact]:
    """Return all contacts owned by the user, with optional filters.

    Args:
        db: Active database session.
        user: The authenticated user whose contacts to retrieve.
        name: Optional partial match on ``first_name``.
        last_name: Optional partial match on ``last_name``.
        email: Optional partial match on ``email``.

    Returns:
        List of matching :class:`models.Contact` instances.
    """
    query = db.query(models.Contact).filter(models.Contact.owner_id == user.id)
    if name:
        query = query.filter(models.Contact.first_name.ilike(f"%{name}%"))
    if last_name:
        query = query.filter(models.Contact.last_name.ilike(f"%{last_name}%"))
    if email:
        query = query.filter(models.Contact.email.ilike(f"%{email}%"))
    return query.all()


def get_contact(db: Session, contact_id: int, user: models.User) -> models.Contact | None:
    """Fetch a single contact by ID, scoped to the given user.

    Args:
        db: Active database session.
        contact_id: Primary key of the requested contact.
        user: The authenticated owner.

    Returns:
        The :class:`models.Contact` instance, or ``None`` if not found.
    """
    return db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.owner_id == user.id,
    ).first()


def delete_contact(db: Session, contact_id: int, user: models.User) -> models.Contact | None:
    """Delete a contact owned by the user.

    Args:
        db: Active database session.
        contact_id: Primary key of the contact to delete.
        user: The authenticated owner.

    Returns:
        The deleted :class:`models.Contact`, or ``None`` if it did not exist.
    """
    contact = get_contact(db, contact_id, user)
    if contact:
        db.delete(contact)
        db.commit()
    return contact


def get_upcoming_birthdays(db: Session, user: models.User) -> list[models.Contact]:
    """Return contacts whose birthday falls within the next 7 days.

    Args:
        db: Active database session.
        user: The authenticated owner.

    Returns:
        List of :class:`models.Contact` instances with upcoming birthdays.
    """
    today = datetime.today().date()
    end_date = today + timedelta(days=7)
    all_contacts = db.query(models.Contact).filter(models.Contact.owner_id == user.id).all()
    upcoming = []
    for contact in all_contacts:
        bday_this_year = contact.birthday.replace(year=today.year)
        if today <= bday_this_year <= end_date:
            upcoming.append(contact)
    return upcoming


def update_contact(
    db: Session,
    contact_id: int,
    body: schemas.ContactBase,
    user: models.User,
) -> models.Contact | None:
    """Update an existing contact owned by the user.

    Args:
        db: Active database session.
        contact_id: Primary key of the contact to update.
        body: New contact data.
        user: The authenticated owner.

    Returns:
        The updated :class:`models.Contact`, or ``None`` if not found.
    """
    db_contact = db.query(models.Contact).filter(
        models.Contact.id == contact_id,
        models.Contact.owner_id == user.id,
    ).first()
    if db_contact:
        db_contact.first_name = body.first_name
        db_contact.last_name = body.last_name
        db_contact.email = body.email
        db_contact.phone = body.phone
        db_contact.birthday = body.birthday
        db_contact.additional_data = body.additional_data
        db.commit()
        db.refresh(db_contact)
    return db_contact


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Look up a user by email address.

    Args:
        db: Active database session.
        email: Email address to search for.

    Returns:
        The :class:`models.User` instance, or ``None`` if not found.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Register a new user with a hashed password.

    Args:
        db: Active database session.
        user: Validated registration payload.

    Returns:
        The newly created :class:`models.User` instance.
    """
    new_user = models.User(
        email=user.email,
        password=auth.get_password_hash(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def verify_user(db: Session, email: str) -> models.User | None:
    """Mark a user's email as verified.

    Args:
        db: Active database session.
        email: Email address of the user to verify.

    Returns:
        The updated :class:`models.User`, or ``None`` if the user does not exist.
    """
    user = get_user_by_email(db, email)
    if user and not user.is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)
    return user


def update_user_avatar(db: Session, user: models.User, url: str) -> models.User:
    """Persist a new avatar URL for the given user.

    Args:
        db: Active database session.
        user: The user whose avatar to update.
        url: New avatar URL (typically a Cloudinary secure URL).

    Returns:
        The updated :class:`models.User` instance.
    """
    user.avatar = url
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, email: str, new_password: str) -> models.User | None:
    """Set a new hashed password for the user identified by *email*.

    Args:
        db: Active database session.
        email: Email address of the target user.
        new_password: Plain-text replacement password (will be hashed).

    Returns:
        The updated :class:`models.User`, or ``None`` if the user does not exist.
    """
    user = get_user_by_email(db, email)
    if user:
        user.password = auth.get_password_hash(new_password)
        db.commit()
        db.refresh(user)
    return user
