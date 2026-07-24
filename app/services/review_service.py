"""
app/services/review_service.py

مدیریت نظرات واقعی کاربران که در صفحه‌ی اصلی نمایش داده می‌شود.
"""

from sqlalchemy.orm import Session

from app.models import ReviewRecord


def create_review(db: Session, user_id: int, rating: int, comment: str) -> ReviewRecord:
    rating = max(1, min(5, rating))

    review = ReviewRecord(
        user_id=user_id,
        rating=rating,
        comment=comment.strip()[:500],
        is_approved=True,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return review


def get_latest_reviews(db: Session, limit: int = 6):
    return (
        db.query(ReviewRecord)
        .filter(ReviewRecord.is_approved.is_(True))
        .order_by(ReviewRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def get_user_reviews(db: Session, user_id: int):
    return (
        db.query(ReviewRecord)
        .filter(ReviewRecord.user_id == user_id)
        .order_by(ReviewRecord.created_at.desc())
        .all()
    )