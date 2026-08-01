"""
app/services/family_service.py
"""

from sqlalchemy.orm import Session

from app.models import FamilyMember


def get_family_members(db: Session, user_id: int) -> list[FamilyMember]:
    return (
        db.query(FamilyMember)
        .filter(FamilyMember.user_id == user_id)
        .order_by(FamilyMember.created_at)
        .all()
    )


def get_family_member_for_user(db: Session, member_id: int, user_id: int) -> FamilyMember | None:
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
    height_cm: int | None = None,
    weight_kg: float | None = None,
    blood_type: str | None = None,
    chronic_diseases: str | None = None,
    allergies: str | None = None,
    current_medications: str | None = None,
    surgeries_history: str | None = None,
    smoking_status: str | None = None,
    activity_level: str | None = None,
) -> FamilyMember:

    member = FamilyMember(
        user_id=user_id,
        name=name,
        relation=relation,
        age=age,
        gender=gender,
        height_cm=height_cm,
        weight_kg=weight_kg,
        blood_type=blood_type or None,
        chronic_diseases=chronic_diseases,
        allergies=allergies,
        current_medications=current_medications,
        surgeries_history=surgeries_history,
        smoking_status=smoking_status or None,
        activity_level=activity_level or None,
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


def update_family_member(
    db: Session,
    member: FamilyMember,
    name: str,
    relation: str | None,
    age: int | None,
    gender: str | None,
    height_cm: int | None,
    weight_kg: float | None,
    blood_type: str | None,
    chronic_diseases: str | None,
    allergies: str | None,
    current_medications: str | None,
    surgeries_history: str | None,
    smoking_status: str | None,
    activity_level: str | None,
) -> FamilyMember:

    member.name = name
    member.relation = relation
    member.age = age
    member.gender = gender
    member.height_cm = height_cm
    member.weight_kg = weight_kg
    member.blood_type = blood_type or None
    member.chronic_diseases = chronic_diseases
    member.allergies = allergies
    member.current_medications = current_medications
    member.surgeries_history = surgeries_history
    member.smoking_status = smoking_status or None
    member.activity_level = activity_level or None

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