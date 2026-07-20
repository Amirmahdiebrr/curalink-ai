"""
app/core/exam_types.py

Single source of truth for exam_type keys and their Persian labels.
Used by report_service (prompt selection + detection), history routes,
and templates, so labels never drift out of sync between files.
"""

EXAM_TYPE_LABELS = {
    "blood": "آزمایش خون",
    "urine": "آزمایش ادرار",
    "biochemistry": "بیوشیمی",
    "sonography": "سونوگرافی",
    "radiology": "رادیولوژی",
    "mri": "MRI",
    "ct_scan": "CT Scan",
    "mammography": "ماموگرافی",
    "hse": "گزارش HSE (طب کار)",
    "other": "سایر",
}

VALID_EXAM_TYPES = list(EXAM_TYPE_LABELS.keys())