"""
app/services/pdf_export_service.py

Renders printable, Persian RTL PDF versions of CuraLink reports
(lab analysis, diet plan, visit-prep summary), with the company
logo in the header and full company info in a footer that repeats
on every page. Uses WeasyPrint, which renders HTML/CSS (including
RTL + complex Persian text shaping) directly to PDF.
"""

from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.core.company_info import COMPANY_INFO
from app.core.logging_config import get_logger

logger = get_logger(__name__)

APP_DIR = Path(__file__).resolve().parent.parent  # .../app
PDF_TEMPLATES_DIR = APP_DIR / "templates" / "pdf"

_env = Environment(loader=FileSystemLoader(str(PDF_TEMPLATES_DIR)))


class PDFExportError(Exception):
    pass


def render_analysis_pdf(
    *,
    patient_name: str,
    exam_type_label: str,
    report_date: datetime,
    symptoms: str | None,
    analysis_html: str,
    organ_groups: list,
) -> bytes:
    """
    گزارش تحلیل آزمایش (شامل جدول عددی نتایج).
    """
    try:
        template = _env.get_template("analysis_report.html")

        html_string = template.render(
            company=COMPANY_INFO,
            patient_name=patient_name,
            exam_type_label=exam_type_label,
            report_date=report_date,
            generated_at=datetime.utcnow(),
            symptoms=symptoms,
            analysis_html=analysis_html,
            organ_groups=organ_groups,
        )

        return HTML(string=html_string, base_url=str(APP_DIR)).write_pdf()

    except Exception as e:
        logger.error(f"[PDFExportService] Failed to render analysis PDF: {e}")
        raise PDFExportError(f"تولید فایل PDF با خطا مواجه شد: {e}")


def render_generic_pdf(
    *,
    document_title: str,
    section_heading: str,
    patient_name: str,
    report_date: datetime,
    content_html: str,
    extra_meta: dict | None = None,
    disclaimer_text: str,
) -> bytes:
    """
    قالب عمومی برای گزارش‌هایی که جدول عددی ندارند: برنامه غذایی و
    آماده‌سازی ویزیت. extra_meta یک دیکشنری ساده {برچسب: مقدار} است
    که در جعبه‌ی اطلاعات بالای گزارش نمایش داده می‌شود (مثلاً دلیل
    مراجعه یا شرح وضعیت خاص کاربر).
    """
    try:
        template = _env.get_template("generic_report.html")

        html_string = template.render(
            company=COMPANY_INFO,
            document_title=document_title,
            section_heading=section_heading,
            patient_name=patient_name,
            report_date=report_date,
            generated_at=datetime.utcnow(),
            content_html=content_html,
            extra_meta=extra_meta or {},
            disclaimer_text=disclaimer_text,
        )

        return HTML(string=html_string, base_url=str(APP_DIR)).write_pdf()

    except Exception as e:
        logger.error(f"[PDFExportService] Failed to render generic PDF: {e}")
        raise PDFExportError(f"تولید فایل PDF با خطا مواجه شد: {e}")