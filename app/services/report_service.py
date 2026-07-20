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

    def _extract_structured_results(self, analysis_text: str):

        match = JSON_BLOCK_PATTERN.search(analysis_text)

        if not match:
            # الگوی دقیق ```json [...] ``` پیدا نشد؛ برای دیباگ،
            # انتهای پاسخ خام را چاپ می‌کنیم تا بفهمیم مدل چه چیزی نوشته.
            tail = analysis_text[-600:] if len(analysis_text) > 600 else analysis_text
            print("[ReportService] No JSON block matched. Raw response tail:", flush=True)
            print(tail, flush=True)

            # تلاش دوم: شاید بلوک بدون فنس کد ```json``` نوشته شده،
            # فقط یک آرایه‌ی JSON خام در انتهای متن باشد.
            fallback_match = re.search(r"(\[\s*\{.*?\}\s*\])\s*$", analysis_text, re.DOTALL)

            if fallback_match:
                try:
                    structured = json.loads(fallback_match.group(1))
                    if isinstance(structured, list):
                        narrative_text = analysis_text[:fallback_match.start()].rstrip()
                        print(f"[ReportService] Fallback JSON extraction succeeded, {len(structured)} item(s)", flush=True)
                        return narrative_text, structured
                except Exception as e:
                    print(f"[ReportService] Fallback JSON parse failed: {e}", flush=True)

            return analysis_text, []

        json_block = match.group(1)

        try:
            structured = json.loads(json_block)
            if not isinstance(structured, list):
                structured = []
        except Exception as e:
            print(f"[ReportService] Failed to parse structured JSON block: {e}", flush=True)
            structured = []

        narrative_text = analysis_text[:match.start()].rstrip()

        return narrative_text, structured

    def _notify(self, on_stage, stage: str):
        if on_stage:
            try:
                on_stage(stage)
            except Exception:
                pass

    async def _ocr_single_file(self, filepath, filename: str, index: int):
        try:
            file_text = await self.ocr.extract(filepath)
        except Exception as e:
            print(f"[ReportService] OCR error on {filepath}: {e}", flush=True)
            return None

        if not file_text.strip():
            return None

        return f"--- بخش {index} از فایل: {filename} ---\n{file_text.strip()}"

    async def _detect_exam_type(self, limited_text: str) -> str | None:
        """
        Asks the AI to classify the actual document type from OCR text,
        independent of what the user selected. Returns a valid exam_type
        key, or None if detection failed / was inconclusive.
        """
        classify_prompt = CLASSIFY_PROMPT_TEMPLATE.format(limited_text[:4000])

        try:
            raw = await self.ai.analyze(classify_prompt)
        except Exception as e:
            print(f"[ReportService] Exam type detection error: {e}", flush=True)
            return None

        cleaned = (raw or "").strip().lower()

        for key in VALID_EXAM_TYPES:
            if key in cleaned:
                return key

        print(f"[ReportService] Exam type detection inconclusive, raw: {cleaned[:200]}", flush=True)
        return None

    async def process(
        self,
        files: list[tuple[bytes, str]],
        exam_type: str = None,
        symptoms: str | None = None,
        on_stage=None,
    ):
        """
        files: لیستی از (بایت‌های فایل, نام اصلی فایل).
        exam_type: نوع آزمایش/تصویربرداری انتخاب‌شده توسط کاربر؛ تعیین‌کننده‌ی
                   پرامپت تخصصی مورد استفاده برای تحلیل (مگر اینکه سیستم
                   تشخیص دهد که نوع واقعی سند متفاوت است، که در آن صورت
                   نوع تشخیص‌داده‌شده جایگزین می‌شود).
        symptoms: شرح علائم یا سابقه‌ی پزشکی که کاربر اختیاری وارد کرده،
                  برای کمک به تفسیر دقیق‌تر AI (در همه‌ی انواع آزمایش/تصویربرداری استفاده می‌شود).
        یک یا چند فایل پشتیبانی می‌شود؛ OCR روی همه‌ی فایل‌ها به‌صورت
        هم‌زمان (parallel) انجام و متن‌ها ترکیب می‌شوند، سپس یک
        فراخوانی واحد به AI برای تحلیل ارسال می‌شود.
        """

        total_start = time.perf_counter()

        print("=" * 50)
        print("START REPORT PROCESS")
        print(f"FILE COUNT: {len(files)}")
        print(f"EXAM TYPE: {exam_type}")
        print(f"HAS SYMPTOMS: {bool(symptoms and symptoms.strip())}")
        print("=" * 50)

        requested_label = EXAM_TYPE_LABELS.get(exam_type, exam_type)
        symptoms_display = self._prepare_symptoms(symptoms)

        self._notify(on_stage, "saving")

        saved_paths = []
        original_names = []

        step_start = time.perf_counter()

        for content, filename in files:
            filepath = self.file_service.save_bytes(filename, content)
            saved_paths.append(filepath)
            original_names.append(filename)
            print(f"FILE SAVED: {filepath}", flush=True)

        print(f"ALL FILES SAVED  [{time.perf_counter() - step_start:.2f}s]", flush=True)

        self._notify(on_stage, "ocr")

        step_start = time.perf_counter()

        ocr_tasks = [
            self._ocr_single_file(filepath, original_names[i], i + 1)
            for i, filepath in enumerate(saved_paths)
        ]

        ocr_results = await asyncio.gather(*ocr_tasks)

        combined_text_parts = [part for part in ocr_results if part]

        ocr_duration = time.perf_counter() - step_start
        text = "\n\n".join(combined_text_parts)

        print(f"OCR DONE FOR ALL FILES (parallel)  [{ocr_duration:.2f}s]", flush=True)
        print(f"COMBINED OCR LENGTH: {len(text)}", flush=True)

        if len(original_names) == 1:
            display_filename = original_names[0]
        else:
            display_filename = f"{original_names[0]} + {len(original_names) - 1} فایل دیگر"

        if not text.strip():
            print("[ReportService] OCR returned empty text for all files", flush=True)
            error_html = self._to_html(
                "متنی از فایل(ها) استخراج نشد. لطفاً تصاویر واضح‌تری آپلود کنید."
            )
            return {
                "filename": display_filename,
                "ocr": text,
                "analysis": "",
                "analysis_html": error_html,
                "structured_results": [],
                "exam_type": exam_type,
                "requested_exam_type": exam_type,
                "requested_exam_type_label": requested_label,
                "exam_type_mismatch": False,
                "detected_exam_type": None,
                "detected_exam_type_label": None,
            }

        limited_text = text[:12000]

        self._notify(on_stage, "ai")

        step_start = time.perf_counter()
        detected_type = await self._detect_exam_type(limited_text)
        detect_duration = time.perf_counter() - step_start
        print(f"[ReportService] Detected exam_type: {detected_type} (requested: {exam_type})  [{detect_duration:.2f}s]", flush=True)

        exam_type_mismatch = False
        final_exam_type = exam_type
        detected_label = None

        if detected_type and exam_type and detected_type != exam_type:
            exam_type_mismatch = True
            final_exam_type = detected_type
            detected_label = EXAM_TYPE_LABELS.get(detected_type, detected_type)
            print(f"[ReportService] MISMATCH: user selected '{exam_type}' but detected '{detected_type}' -> using detected type", flush=True)

        prompt_template = get_prompt_template(final_exam_type)
        prompt = prompt_template.format(text=limited_text, symptoms=symptoms_display)

        print(f"PROMPT LENGTH: {len(prompt)}", flush=True)

        step_start = time.perf_counter()
        raw_analysis = await self.ai.analyze(prompt)
        ai_duration = time.perf_counter() - step_start
        print(f"AI DONE  [{ai_duration:.2f}s]", flush=True)

        narrative_text, structured_results = self._extract_structured_results(raw_analysis)

        print(f"[ReportService] Extracted {len(structured_results)} structured test result(s)", flush=True)

        analysis_html = self._to_html(narrative_text)

        total_duration = time.perf_counter() - total_start
        print("=" * 50)
        print(f"TOTAL TIME: {total_duration:.2f}s  (OCR: {ocr_duration:.2f}s | Detect: {detect_duration:.2f}s | AI: {ai_duration:.2f}s)")
        print("=" * 50)

        self._notify(on_stage, "done")

        return {
            "filename": display_filename,
            "ocr": text,
            "analysis": narrative_text,
            "analysis_html": analysis_html,
            "structured_results": structured_results,
            "exam_type": final_exam_type,
            "requested_exam_type": exam_type,
            "requested_exam_type_label": requested_label,
            "exam_type_mismatch": exam_type_mismatch,
            "detected_exam_type": detected_type,
            "detected_exam_type_label": detected_label,
        }