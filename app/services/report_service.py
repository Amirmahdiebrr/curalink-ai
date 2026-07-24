import time
import json
import re
import asyncio

import markdown
import bleach

from app.services.file_service import FileService
from app.services.ocr_service import OCRService
from app.services.ai_service import AIService

from app.prompts.exam_prompts import get_prompt_template
from app.prompts.classify_prompt import CLASSIFY_PROMPT_TEMPLATE
from app.core.exam_types import EXAM_TYPE_LABELS, VALID_EXAM_TYPES
from app.core.logging_config import get_logger

logger = get_logger(__name__)


JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\[.*?\])\s*```", re.DOTALL)


ALLOWED_TAGS = [
    "h1", "h2", "h3", "h4",
    "p", "br", "hr",
    "ul", "ol", "li",
    "strong", "em", "b", "i",
    "table", "thead", "tbody", "tr", "th", "td",
    "a",
    "blockquote", "code", "pre",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "rel", "target"],
}

MAX_SYMPTOMS_LENGTH = 1000

NO_SYMPTOMS_TEXT = "کاربر شرحی وارد نکرده است."

GENDER_LABELS = {
    "male": "مرد",
    "female": "زن",
    "other": "سایر",
}

NO_PROFILE_TEXT = "اطلاعاتی از سن/جنسیت کاربر در دسترس نیست."

# سقف کل متن ارسالی به AI و سهم هر فایل از این سقف، برای اطمینان از
# این‌که در آنالیزهای چندفایلی، فایل‌های بعدی هم واقعاً به مدل می‌رسند
# (نه این‌که فقط فایل اول کل بودجه‌ی کاراکتر را مصرف کند).
TOTAL_TEXT_BUDGET = 20000
CLASSIFY_TEXT_BUDGET = 6000


class ReportService:

    def __init__(self):
        self.file_service = FileService()
        self.ocr = OCRService()
        self.ai = AIService()

    def _to_html(self, text: str) -> str:
        raw_html = markdown.markdown(
            text,
            extensions=["extra", "nl2br", "sane_lists"]
        )

        clean_html = bleach.clean(
            raw_html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            strip=True,
        )

        return clean_html

    def _prepare_symptoms(self, symptoms: str | None) -> str:
        if not symptoms:
            return NO_SYMPTOMS_TEXT

        cleaned = symptoms.strip()

        if not cleaned:
            return NO_SYMPTOMS_TEXT

        return cleaned[:MAX_SYMPTOMS_LENGTH]

    def _prepare_patient_profile(self, age: int | None, gender: str | None) -> str:
        parts = []

        if age is not None:
            parts.append(f"سن: {age} سال")

        if gender:
            gender_label = GENDER_LABELS.get(gender)
            if gender_label:
                parts.append(f"جنسیت: {gender_label}")

        if not parts:
            return NO_PROFILE_TEXT

        return " | ".join(parts)

    def _extract_structured_results(self, analysis_text: str):

        match = JSON_BLOCK_PATTERN.search(analysis_text)

        if not match:
            tail = analysis_text[-600:] if len(analysis_text) > 600 else analysis_text
            logger.warning("[ReportService] No JSON block matched. Raw response tail:")
            logger.warning(tail)

            fallback_match = re.search(r"(\[\s*\{.*?\}\s*\])\s*$", analysis_text, re.DOTALL)

            if fallback_match:
                try:
                    structured = json.loads(fallback_match.group(1))
                    if isinstance(structured, list):
                        narrative_text = analysis_text[:fallback_match.start()].rstrip()
                        logger.info(f"[ReportService] Fallback JSON extraction succeeded, {len(structured)} item(s)")
                        return narrative_text, structured
                except Exception as e:
                    logger.error(f"[ReportService] Fallback JSON parse failed: {e}")

            return analysis_text, []

        json_block = match.group(1)

        try:
            structured = json.loads(json_block)
            if not isinstance(structured, list):
                structured = []
        except Exception as e:
            logger.error(f"[ReportService] Failed to parse structured JSON block: {e}")
            structured = []

        narrative_text = analysis_text[:match.start()].rstrip()

        return narrative_text, structured

    def _notify(self, on_stage, stage: str):
        if on_stage:
            try:
                on_stage(stage)
            except Exception:
                pass

    def _cleanup_files(self, paths: list):
        for filepath in paths:
            try:
                if filepath.exists():
                    filepath.unlink()
                    logger.info(f"[ReportService] Cleaned up file: {filepath}")
            except Exception as e:
                logger.error(f"[ReportService] Failed to clean up file {filepath}: {e}")

    async def _ocr_single_file(self, filepath, filename: str, index: int):
        try:
            file_text = await self.ocr.extract(filepath)
        except Exception as e:
            logger.error(f"[ReportService] OCR error on {filepath}: {e}")
            return None, filename

        if not file_text.strip():
            return None, filename

        return f"--- بخش {index} از فایل: {filename} ---\n{file_text.strip()}", None

    def _build_limited_text(self, combined_parts: list[str]) -> str:
        """
        به‌جای برش کورکورانه‌ی متن ترکیب‌شده (که می‌تواند فایل‌های بعدی را
        کاملاً حذف کند)، سهم هر فایل از سقف کل کاراکتر را جداگانه محاسبه
        می‌کند تا هر فایل حداقل بخشی از متنش به مدل برسد.
        """
        if not combined_parts:
            return ""

        per_file_budget = max(TOTAL_TEXT_BUDGET // len(combined_parts), 1500)

        trimmed_parts = [part[:per_file_budget] for part in combined_parts]

        limited = "\n\n".join(trimmed_parts)

        return limited[:TOTAL_TEXT_BUDGET]

    def _notify_ocr_failures(self, failed_filenames: list[str]) -> str | None:
        if not failed_filenames:
            return None

        names = "، ".join(failed_filenames)
        return f"⚠️ استخراج متن از {len(failed_filenames)} فایل ({names}) ناموفق بود و این فایل(ها) در تحلیل نهایی لحاظ نشده‌اند."

    async def _detect_exam_type(self, limited_text: str) -> str | None:
        classify_prompt = CLASSIFY_PROMPT_TEMPLATE.format(limited_text[:CLASSIFY_TEXT_BUDGET])

        try:
            raw = await self.ai.analyze(classify_prompt)
        except Exception as e:
            logger.error(f"[ReportService] Exam type detection error: {e}")
            return None

        cleaned = (raw or "").strip().lower()

        for key in VALID_EXAM_TYPES:
            if key in cleaned:
                return key

        logger.warning(f"[ReportService] Exam type detection inconclusive, raw: {cleaned[:200]}")
        return None

    async def process(
        self,
        files: list[tuple[bytes, str]],
        exam_type: str = None,
        symptoms: str | None = None,
        patient_age: int | None = None,
        patient_gender: str | None = None,
        on_stage=None,
    ):
        """
        files: لیستی از (بایت‌های فایل, نام اصلی فایل).
        patient_age / patient_gender: اطلاعات پروفایل کاربر (در صورت وجود در پروفایلش)،
                  برای کمک به تفسیر دقیق‌تر بازه‌های مرجع سن/جنسیت‌محور در پرامپت‌های AI.
        """

        total_start = time.perf_counter()

        logger.info("=" * 50)
        logger.info("START REPORT PROCESS")
        logger.info(f"FILE COUNT: {len(files)}")
        logger.info(f"EXAM TYPE: {exam_type}")
        logger.info(f"HAS SYMPTOMS: {bool(symptoms and symptoms.strip())}")
        logger.info(f"PATIENT AGE/GENDER: {patient_age} / {patient_gender}")
        logger.info("=" * 50)

        requested_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)

        # ==========================
        # 1) Save + validate files to disk (OCR needs a filepath)
        # ==========================
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

        # ==========================
        # 2) OCR every saved file (concurrently)
        # ==========================
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
        # 3) Detect the *actual* exam type from the OCR text,
        #    independent of what the user selected in the upload form.
        # ==========================
        detected_exam_type = await self._detect_exam_type(limited_text)

        final_exam_type = exam_type
        exam_type_mismatch = False

        if detected_exam_type and exam_type and detected_exam_type != exam_type:
            exam_type_mismatch = True
            final_exam_type = detected_exam_type
            logger.info(
                f"[ReportService] Exam type mismatch: requested={exam_type}, detected={detected_exam_type}"
            )
        elif detected_exam_type and not exam_type:
            final_exam_type = detected_exam_type

        # ==========================
        # 4) Build the specialized prompt for the final exam type and call the AI
        # ==========================
        self._notify(on_stage, "ai")

        symptoms_display = self._prepare_symptoms(symptoms)
        patient_profile = self._prepare_patient_profile(patient_age, patient_gender)

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
            f"structured_results: {len(structured_results)}"
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