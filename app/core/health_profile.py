"""
app/core/health_profile.py

منبع مشترک فیلدهای پروفایل سلامت اولیه (قد/وزن/گروه خونی/بیماری
مزمن/حساسیت/داروها/سیگار/سطح فعالیت) و تبدیل آن‌ها به متنی که در
پرامپت‌های تحلیل آزمایش، برنامه غذایی، آماده‌سازی ویزیت و برنامه
ورزشی تزریق می‌شود.
"""

GENDER_LABELS = {
    "male": "مرد",
    "female": "زن",
    "other": "سایر",
}

SMOKING_LABELS = {
    "none": "غیرسیگاری",
    "occasional": "گاه‌به‌گاه",
    "regular": "سیگاری منظم",
}

ACTIVITY_LABELS = {
    "sedentary": "کم‌تحرک (بدون ورزش منظم)",
    "light": "فعالیت سبک (۱-۲ روز در هفته)",
    "moderate": "فعالیت متوسط (۳-۴ روز در هفته)",
    "active": "فعال (۵-۶ روز در هفته)",
    "very_active": "بسیار فعال / ورزشکار حرفه‌ای",
}

BLOOD_TYPE_OPTIONS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

NO_HEALTH_PROFILE_TEXT = "اطلاعات سلامت اولیه‌ای برای این فرد ثبت نشده است."

HEALTH_PROFILE_FIELD_NAMES = [
    "age", "gender", "height_cm", "weight_kg", "blood_type",
    "chronic_diseases", "allergies", "current_medications",
    "surgeries_history", "smoking_status", "activity_level",
]


def compute_bmi(height_cm, weight_kg):
    if not height_cm or not weight_kg:
        return None
    try:
        height_m = height_cm / 100
        if height_m <= 0:
            return None
        return round(weight_kg / (height_m ** 2), 1)
    except (TypeError, ZeroDivisionError):
        return None


def person_health_fields(person) -> dict:
    """
    person: نمونه‌ی ORM از User یا FamilyMember (یا None).
    """
    if person is None:
        return {}

    return {name: getattr(person, name, None) for name in HEALTH_PROFILE_FIELD_NAMES}


def build_health_profile_text(fields: dict | None) -> str:
    if not fields:
        return NO_HEALTH_PROFILE_TEXT

    lines = []

    age = fields.get("age")
    gender = fields.get("gender")
    height_cm = fields.get("height_cm")
    weight_kg = fields.get("weight_kg")

    if age is not None:
        lines.append(f"سن: {age} سال")

    gender_label = GENDER_LABELS.get(gender)
    if gender_label:
        lines.append(f"جنسیت: {gender_label}")

    if height_cm:
        lines.append(f"قد: {height_cm} سانتی‌متر")

    if weight_kg:
        lines.append(f"وزن: {weight_kg} کیلوگرم")

    bmi = compute_bmi(height_cm, weight_kg)
    if bmi:
        lines.append(f"شاخص توده بدنی (BMI): {bmi}")

    blood_type = fields.get("blood_type")
    if blood_type:
        lines.append(f"گروه خونی: {blood_type}")

    activity_label = ACTIVITY_LABELS.get(fields.get("activity_level"))
    if activity_label:
        lines.append(f"سطح فعالیت بدنی: {activity_label}")

    smoking_label = SMOKING_LABELS.get(fields.get("smoking_status"))
    if smoking_label:
        lines.append(f"وضعیت سیگار/دخانیات: {smoking_label}")

    chronic_diseases = (fields.get("chronic_diseases") or "").strip()
    if chronic_diseases:
        lines.append(f"سابقه بیماری‌های مزمن: {chronic_diseases}")

    surgeries_history = (fields.get("surgeries_history") or "").strip()
    if surgeries_history:
        lines.append(f"سابقه جراحی: {surgeries_history}")

    allergies = (fields.get("allergies") or "").strip()
    if allergies:
        lines.append(f"حساسیت‌ها: {allergies}")

    medications = (fields.get("current_medications") or "").strip()
    if medications:
        lines.append(f"داروهای مصرفی فعلی: {medications}")

    if not lines:
        return NO_HEALTH_PROFILE_TEXT

    return "\n".join(f"- {line}" for line in lines)