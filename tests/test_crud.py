"""Unit tests for the crud module."""
import pytest
from datetime import date
import crud, schemas, models


def test_create_and_get_user(db):
    user_data = schemas.UserCreate(email="crudtest@example.com", password="pass123")
    user = crud.create_user(db, user_data)
    assert user.id is not None
    assert user.email == "crudtest@example.com"

    fetched = crud.get_user_by_email(db, "crudtest@example.com")
    assert fetched.id == user.id

    db.delete(user)
    db.commit()


def test_verify_user(db):
    user_data = schemas.UserCreate(email="verify@example.com", password="pass123")
    user = crud.create_user(db, user_data)
    assert not user.is_verified

    verified = crud.verify_user(db, user.email)
    assert verified.is_verified

    db.delete(verified)
    db.commit()


def test_create_and_delete_contact(db, test_user):
    contact_data = schemas.ContactBase(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone="1234567890",
        birthday=date(1990, 6, 15),
    )
    contact = crud.create_contact(db, contact_data, test_user)
    assert contact.id is not None
    assert contact.owner_id == test_user.id

    deleted = crud.delete_contact(db, contact.id, test_user)
    assert deleted is not None

    assert crud.get_contact(db, contact.id, test_user) is None


def test_update_contact(db, test_user):
    contact_data = schemas.ContactBase(
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        phone="0987654321",
        birthday=date(1995, 3, 10),
    )
    contact = crud.create_contact(db, contact_data, test_user)

    updated_data = schemas.ContactBase(
        first_name="Janet",
        last_name="Smith",
        email="janet@example.com",
        phone="0987654321",
        birthday=date(1995, 3, 10),
    )
    updated = crud.update_contact(db, contact.id, updated_data, test_user)
    assert updated.first_name == "Janet"

    db.delete(updated)
    db.commit()


def test_get_contacts_with_filter(db, test_user):
    c1 = crud.create_contact(db, schemas.ContactBase(
        first_name="Alice", last_name="Wonder", email="alice@example.com",
        phone="111", birthday=date(1992, 1, 1)
    ), test_user)
    c2 = crud.create_contact(db, schemas.ContactBase(
        first_name="Bob", last_name="Builder", email="bob@example.com",
        phone="222", birthday=date(1993, 2, 2)
    ), test_user)

    results = crud.get_contacts(db, test_user, name="Alice")
    names = [c.first_name for c in results]
    assert "Alice" in names
    assert "Bob" not in names

    db.delete(c1)
    db.delete(c2)
    db.commit()


def test_reset_user_password(db):
    user_data = schemas.UserCreate(email="resetpwd@example.com", password="oldpass")
    user = crud.create_user(db, user_data)

    updated = crud.reset_user_password(db, user.email, "newpass123")
    import auth
    assert auth.verify_password("newpass123", updated.password)

    db.delete(updated)
    db.commit()


def test_update_user_avatar(db, test_user):
    updated = crud.update_user_avatar(db, test_user, "http://example.com/avatar.png")
    assert updated.avatar == "http://example.com/avatar.png"
