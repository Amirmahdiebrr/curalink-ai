"""
tests/test_organ_display_service.py

تست‌های حداقلی برای گروه‌بندی نتایج آزمایش بر اساس ارگان و محاسبه‌ی
موقعیت نوار مقدار/بازه‌ی مرجع — منطقی که مستقیم در صفحه‌ی نتیجه به
کاربر نمایش داده می‌شود.
"""

from app.services.organ_display_service import group_results_by_organ, _parse_reference_range, _compute_bar


def test_parse_reference_range_valid():
    result = _parse_reference_range("4-10")
    assert result == (4.0, 10.0)


def test_parse_reference_range_invalid_returns_none():
    assert _parse_reference_range("نامشخص") is None
    assert _parse_reference_range(None) is None


def test_compute_bar_flags_severe_when_far_outside_range():
    bar = _compute_bar(20.0, "4-10")
    assert bar is not None
    assert bar["severity"] == "severe"


def test_compute_bar_normal_within_range():
    bar = _compute_bar(6.0, "4-10")
    assert bar is not None
    assert bar["severity"] is None


def test_group_results_by_organ_buckets_correctly():
    results = [
        {"name": "WBC", "value": 6.5, "unit": "10^3/uL", "reference_range": "4-10", "status": "normal", "organ_category": "blood"},
        {"name": "Glucose", "value": 200, "unit": "mg/dL", "reference_range": "70-100", "status": "high", "organ_category": "metabolic"},
        {"name": "Unknown", "value": 1, "unit": "", "reference_range": "", "status": "normal", "organ_category": "not_a_real_category"},
    ]

    groups = group_results_by_organ(results)

    keys = [g["key"] for g in groups]
    assert "blood" in keys
    assert "metabolic" in keys
    assert "other" in keys  # unknown category falls back to "other"

    blood_group = next(g for g in groups if g["key"] == "blood")
    assert blood_group["items"][0]["name"] == "WBC"