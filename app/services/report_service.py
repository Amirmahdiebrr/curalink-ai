"""
app/services/report_service.py
"""

import json
import asyncio
import re
import time
from pathlib import Path

import markdown
import bleach

from app.core.exam_types import EXAM_TYPE_LABELS, VALID_EXAM_TYPES
from app.core.logging_config import get_logger
from app.core.health_profile import build_health_profile_text
from app.prompts.exam_prompts import get_prompt_template
from app.prompts.classify_prompt import CLASSIFY_PROMPT_TEMPLATE
from app.services.file_service import FileService
from app.services.ocr_service import OCRService, OCRServiceError
from app.services.ai_service import AIService

logger = get_logger(__name__)

MAX_PROMPT_TEXT_LENGTH = 14000

NO_SYMPTOMS_TEXT = "کاربر علائم یا سابقه‌ی پزشکی خاصی وارد نکرده است."

ALLOWED_TAGS = [
    "p", "br", "hr",
    "h1", "h2", "h3", "h4",
    "ul", "ol", "li",
    "strong", "b", "em", "i",
    "table", "thead", "tbody", "tr", "th", "td",
    "blockquote", "code", "pre",
    "a", "span",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
}


class ReportService:

    def __init__(self):
        self.file_service = FileService()
        self.ocr_service = OCRService()
        self.ai = AIService()

    def _notify(self, on_stage, stage: str):
        if on_stage:
            try:
                on_stage(stage)
            except Exception as e:
                logger.warning(f"[ReportService] on_stage callback failed: {e}")

    def _cleanup_files(self, saved_paths: list[Path]):
        for path in saved_paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.warning(f"[ReportService] Failed to remove temp file {path}: {e}")

    async def _ocr_single_file(self, filepath: Path, filename: str, index: int):
        try:
            text = await self.ocr_service.extract(filepath)
        except OCRServiceError as e:
            logger.warning(f"[ReportService] OCR failed for {filename}: {e}")
            return None, filename
        except Exception as e:
            logger.error(f"[ReportService] Unexpected OCR error for {filename}: {e}")
            return None, filename

        part = f"--- فایل {index}: {filename} ---\n{text}"
        return part, None

    def _notify_ocr_failures(self, failed_filenames: list[str]):
        if not failed_filenames:
            return None

        names = "، ".join(failed_filenames)
        return f"⚠️ استخراج متن از {len(failed_filenames)} فایل ناموفق بود: {names}"

    def _build_limited_text(self, combined_parts: list[str]) -> str:
        full_text = "\n\n".join(combined_parts)

        if len(full_text) <= MAX_PROMPT_TEXT_LENGTH:
            return full_text

        return full_text[:MAX_PROMPT_TEXT_LENGTH]

    def _prepare_symptoms(self, symptoms: str | None) -> str:
        if not symptoms:
            return NO_SYMPTOMS_TEXT

        cleaned = symptoms.strip()

        if not cleaned:
            return NO_SYMPTOMS_TEXT

        return cleaned[:1000]

    async def _detect_exam_type(self, limited_text: str) -> str | None:
        try:
            prompt = CLASSIFY_PROMPT_TEMPLATE.format(limited_text)
            raw = await self.ai.analyze(prompt)
        except Exception as e:
            logger.warning(f"[ReportService] Exam type detection failed: {e}")
            return None

        detected = (raw or "").strip().lower()

        for exam_type in VALID_EXAM_TYPES:
            if exam_type in detected:
                return exam_type

        return None

    def _extract_structured_results(self, raw_analysis: str):
        match = re.search(r"```json\s*(\[.*?\])\s*```", raw_analysis, re.DOTALL)

        if not match:
            return raw_analysis.strip(), []

        json_block = match.group(1)
        narrative_text = raw_analysis[:match.start()].strip()

        try:
            structured_results = json.loads(json_block)
            if not isinstance(structured_results, list):
                structured_results = []
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[ReportService] Failed to parse structured JSON block: {e}")
            structured_results = []

        return narrative_text, structured_results

    def _to_html(self, narrative_text: str) -> str:
        raw_html = markdown.markdown(narrative_text, extensions=["extra", "nl2br", "sane_lists"])
        return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

    async def process(
        self,
        files: list[tuple[bytes, str]],
        exam_type: str = None,
        symptoms: str | None = None,
        health_profile_fields: dict | None = None,
        on_stage=None,
    ):
        total_start = time.perf_counter()

        logger.info("=" * 50)
        logger.info("START REPORT PROCESS")
        logger.info(f"FILE COUNT: {len(files)}")
        logger.info(f"EXAM TYPE: {exam_type}")
        logger.info(f"HAS SYMPTOMS: {bool(symptoms and symptoms.strip())}")
        logger.info("=" * 50)

        requested_exam_type = exam_type if exam_type in VALID_EXAM_TYPES else None
        requested_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)

        self._notify(on_stage, "saving")

        saved_paths = []
        original_names = []

        for content, original_filename in files:
            try:
                filepath = self.file_service.save_bytes(original_filename, content)
            except Exception as e:
                logger.error(f"[ReportService] File validation/save failed for {original_filename}: {e}")
                continue

            saved_paths.append(filepath)
            original_names.append(original_filename)

        if not saved_paths:
            raise Exception("هیچ‌کدام از فایل‌های ارسالی معتبر نبودند یا ذخیره نشدند.")

        self._notify(on_stage, "ocr")

        ocr_tasks = [
            self._ocr_single_file(filepath, filename, index + 1)
            for index, (filepath, filename) in enumerate(zip(saved_paths, original_names))
        ]

        ocr_results = await asyncio.gather(*ocr_tasks)

        self._cleanup_files(saved_paths)

        combined_parts = []
        full_ocr_parts = []
        failed_filenames = []

        for part_text, failed_filename in ocr_results:
            if part_text:
                combined_parts.append(part_text)
                full_ocr_parts.append(part_text)
            if failed_filename:
                failed_filenames.append(failed_filename)

        if not combined_parts:
            raise Exception("استخراج متن از هیچ‌یک از فایل‌های ارسالی موفق نبود.")

        full_ocr_text = "\n\n".join(full_ocr_parts)
        limited_text = self._build_limited_text(combined_parts)

        ocr_warning = self._notify_ocr_failures(failed_filenames)

        # ==========================
        # تشخیص نوع آزمایش:
        # - اگر کاربر اصلاً نوعی انتخاب نکرده (یا نامعتبر بوده)، همیشه تشخیص AI اجرا می‌شود.
        # - اگر کاربر نوع معتبری انتخاب کرده، باز هم تشخیص AI اجرا می‌شود تا با
        #   انتخاب کاربر مقایسه شود و در صورت اختلاف به او هشدار داده شود.
        # ==========================
        detected_exam_type = await self._detect_exam_type(limited_text)

        if requested_exam_type:
            final_exam_type = requested_exam_type
            exam_type_mismatch = bool(
                detected_exam_type and detected_exam_type != requested_exam_type
            )
        else:
            final_exam_type = detected_exam_type or "other"
            exam_type_mismatch = False

        self._notify(on_stage, "ai")

        symptoms_display = self._prepare_symptoms(symptoms)
        patient_profile = build_health_profile_text(health_profile_fields)

        prompt_template = get_prompt_template(final_exam_type)

        prompt = prompt_template.format(
            text=limited_text,
            symptoms=symptoms_display,
            patient_profile=patient_profile,
        )

        raw_analysis = await self.ai.analyze(prompt)

        narrative_text, structured_results = self._extract_structured_results(raw_analysis)

        analysis_html = self._to_html(narrative_text)

        total_elapsed = time.perf_counter() - total_start

        logger.info(
            f"[ReportService] Finished in {total_elapsed:.2f}s, "
            f"structured_results: {len(structured_results)}, "
            f"exam_type_mismatch: {exam_type_mismatch}"
        )

        if len(original_names) == 1:
            filename_display = original_names[0]
        else:
            filename_display = f"{original_names[0]} و {len(original_names) - 1} فایل دیگر"

        return {
            "exam_type": final_exam_type,
            "filename": filename_display,
            "ocr": full_ocr_text,
            "analysis": narrative_text,
            "analysis_html": analysis_html,
            "structured_results": structured_results,
            "symptoms": (symptoms or "").strip() or None,
            "exam_type_mismatch": exam_type_mismatch,
            "requested_exam_type_label": requested_label if exam_type_mismatch else None,
            "detected_exam_type_label": (
                EXAM_TYPE_LABELS.get(detected_exam_type, detected_exam_type)
                if exam_type_mismatch else None
            ),
            "ocr_warning": ocr_warning,
        }