"""
app/services/auth_service.py

Local user record management, tied to WordPress-authenticated identity.
Passwords are never stored here - authentication happens via WordPress.
"""

from sqlalchemy.orm import Session

from app.models import LocalUser


def get_user_by_email(db: Session, email: str) -> LocalUser | None:
    return db.query(LocalUser).filter(LocalUser.email == email).first()


def get_or_create_user(
    db: Session,
    email: str,
    nicename: str | None,
    display_name: str | None,
) -> LocalUser:
    """
    Finds the local user record matching this WordPress account,
    or creates one on first login.
    """

    user = get_user_by_email(db, email)

    if user:
        # Keep name info in sync with WordPress in case it changed
        user.nicename = nicename
        user.display_name = display_name
        db.commit()
        db.refresh(user)
        return user

    user = LocalUser(
        email=email,
        nicename=nicename,
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user