"""
app/services/family_service.py

Manages family member profiles belonging to a logged-in user.
"""

from sqlalchemy.orm import Session

from app.models import FamilyMember


def get_family_members(db: Session, user_id: int):
    return (
        db.query(FamilyMember)
        .filter(FamilyMember.user_id == user_id)
        .order_by(FamilyMember.created_at)
        .all()
    )


def get_family_member_for_user(db: Session, member_id: int, user_id: int):
    return (
        db.query(FamilyMember)
        .filter(FamilyMember.id == member_id, FamilyMember.user_id == user_id)
        .first()
    )


def create_family_member(
    db: Session,
    user_id: int,
    name: str,
    relation: str | None,
    age: int | None,
    gender: str | None,
) -> FamilyMember:

    member = FamilyMember(
        user_id=user_id,
        name=name.strip(),
        relation=relation.strip() if relation else None,
        age=age,
        gender=gender,
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


def delete_family_member(db: Session, member_id: int, user_id: int) -> bool:
    member = get_family_member_for_user(db, member_id, user_id)

    if not member:
        return False

    db.delete(member)
    db.commit()
    return True