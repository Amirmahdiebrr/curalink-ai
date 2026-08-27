"""
tests/test_report_service.py

تست‌های حداقلی برای منطق استخراج ساختاریافته و ساخت HTML گزارش
(بخش‌هایی از ReportService که وابسته به فایل/OCR/AI واقعی نیستند).
AI واقعی و OCR واقعی صدا زده نمی‌شوند — این تست‌ها فقط منطق پردازش
متن خروجی مدل را بررسی می‌کنند.
"""

from app.services.report_service import ReportService


def test_extract_structured_results_parses_valid_json_block():
    service = ReportService()

    raw = (
        "# خلاصه وضعیت\nهمه‌چیز طبیعی است.\n\n"
        '```json\n[{"name": "WBC", "value": 6.5, "unit": "10^3/uL", '
        '"reference_range": "4-10", "status": "normal", '
        '"recommended_followup_days": null, "organ_category": "blood"}]\n```'
    )

    narrative, structured = service._extract_structured_results(raw)

    assert "خلاصه وضعیت" in narrative
    assert len(structured) == 1
    assert structured[0]["name"] == "WBC"
    assert structured[0]["status"] == "normal"


def test_extract_structured_results_handles_missing_json_block():
    service = ReportService()

    raw = "# خلاصه وضعیت\nهیچ بلوک JSON‌ای اینجا نیست."

    narrative, structured = service._extract_structured_results(raw)

    assert narrative == raw.strip()
    assert structured == []


def test_extract_structured_results_handles_malformed_json():
    service = ReportService()

    raw = "# خلاصه\nمتن\n```json\n[{invalid json here}]\n```"

    narrative, structured = service._extract_structured_results(raw)

    assert structured == []


def test_to_html_strips_disallowed_tags():
    service = ReportService()

    html = service._to_html("# عنوان\n\nمتن با <script>alert(1)</script> خطرناک.")

    assert "<script>" not in html
    assert "عنوان" in html


def test_build_limited_text_truncates_long_text():
    service = ReportService()

    long_parts = ["x" * 20000]
    limited = service._build_limited_text(long_parts)

    from app.services.report_service import MAX_PROMPT_TEXT_LENGTH
    assert len(limited) == MAX_PROMPT_TEXT_LENGTH


def test_prepare_symptoms_returns_default_text_when_empty():
    service = ReportService()

    result = service._prepare_symptoms(None)

    assert "علائم" in result or "سابقه" in result


def test_prepare_symptoms_truncates_long_input():
    service = ReportService()

    long_symptoms = "ع" * 2000
    result = service._prepare_symptoms(long_symptoms)

    assert len(result) == 1000