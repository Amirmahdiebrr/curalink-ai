"""
app/services/organ_display_service.py

Groups structured test results by organ/system category and computes
simple range-bar positioning data so the result page can render a
visual bar (like value-within-reference-range) for each test.
"""

import re
from collections import OrderedDict


ORGAN_LABELS = {
    "blood": ("خون‌شناسی", "🩸"),
    "metabolic": ("متابولیک (قند و چربی)", "🍬"),
    "liver": ("کبد", "🫁"),
    "kidney": ("کلیه", "🫘"),
    "thyroid": ("تیروئید", "🦋"),
    "cardiac": ("قلب", "❤️"),
    "urine": ("ادرار", "💧"),
    "vitamin_mineral": ("ویتامین‌ها و مواد معدنی", "🥕"),
    "other": ("سایر", "🔬"),
}

ORGAN_ORDER = ["blood", "metabolic", "liver", "kidney", "thyroid", "cardiac", "urine", "vitamin_mineral", "other"]

STATUS_LABELS = {
    "high": "بالا",
    "low": "پایین",
    "normal": "طبیعی",
}


def _parse_reference_range(range_str):
    if not range_str:
        return None

    cleaned = str(range_str).strip()

    match = re.match(r'^(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)$', cleaned)

    if not match:
        return None

    try:
        rmin = float(match.group(1))
        rmax = float(match.group(2))
    except ValueError:
        return None

    if rmax <= rmin:
        return None

    return rmin, rmax


def _compute_bar(value, reference_range):
    parsed = _parse_reference_range(reference_range)

    if parsed is None or value is None:
        return None

    rmin, rmax = parsed
    span = rmax - rmin

    padded_min = rmin - span * 0.3
    padded_max = rmax + span * 0.3
    total = padded_max - padded_min

    if total <= 0:
        return None

    def to_pct(v):
        pct = (v - padded_min) / total * 100
        return max(0, min(100, pct))

    return {
        "value_pct": to_pct(value),
        "range_start_pct": to_pct(rmin),
        "range_end_pct": to_pct(rmax),
    }


def group_results_by_organ(structured_results: list):
    """
    Accepts a list of dicts (or objects with the same attributes) each
    having: name, value, unit, reference_range, status, organ_category.
    Returns an ordered list of group dicts:
    [{"key", "label", "icon", "items": [...]}]
    Groups with no items are omitted.
    """

    buckets = OrderedDict((key, []) for key in ORGAN_ORDER)

    for item in structured_results:
        if isinstance(item, dict):
            name = item.get("name")
            value = item.get("value")
            unit = item.get("unit")
            reference_range = item.get("reference_range")
            status = item.get("status")
            organ_category = item.get("organ_category")
        else:
            name = getattr(item, "test_name", None) or getattr(item, "name", None)
            value = getattr(item, "value_numeric", None)
            if value is None:
                value = getattr(item, "value", None)
            unit = getattr(item, "unit", None)
            reference_range = getattr(item, "reference_range", None)
            status = getattr(item, "status", None)
            organ_category = getattr(item, "organ_category", None)

        if not name:
            continue

        if organ_category not in buckets:
            organ_category = "other"

        try:
            numeric_value = float(value) if value is not None else None
        except (TypeError, ValueError):
            numeric_value = None

        bar = _compute_bar(numeric_value, reference_range)

        buckets[organ_category].append({
            "name": name,
            "value": value,
            "unit": unit or "",
            "reference_range": reference_range or "—",
            "status": status,
            "status_label": STATUS_LABELS.get(status, status or "نامشخص"),
            "bar": bar,
        })

    groups = []

    for key in ORGAN_ORDER:
        items = buckets[key]
        if not items:
            continue

        label, icon = ORGAN_LABELS[key]
        groups.append({
            "key": key,
            "label": label,
            "icon": icon,
            "items": items,
        })

    return groups