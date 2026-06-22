from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Date, Text, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum


class UserRole(str, enum.Enum):
    """Enumeration of available user roles."""
    user = "user"
    admin = "admin"


class User(Base):
    """SQLAlchemy model representing a registered user.

    Attributes:
        id: Primary key.
        email: Unique email address.
        password: Hashed password.
        created_at: Registration timestamp.
        avatar: URL to the user's avatar image.
        is_verified: Whether the email is verified.
        role: User role (user or admin).
        contacts: Related contacts owned by this user.
    """

    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    avatar = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    contacts = relationship("Contact", back_populates="owner")


class Contact(Base):
    """SQLAlchemy model representing a contact.

    Attributes:
        id: Primary key.
        first_name: Contact's first name.
        last_name: Contact's last name.
        email: Contact's email address.
        phone: Contact's phone number.
        birthday: Contact's date of birth.
        additional_data: Optional extra information.
        owner_id: Foreign key to the owning user.
        owner: Related User object.
    """

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    phone = Column(String, nullable=False)
    birthday = Column(Date, nullable=False)
    additional_data = Column(Text, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="contacts")
