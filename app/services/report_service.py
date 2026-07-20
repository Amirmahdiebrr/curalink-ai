import time
import json
import re
import asyncio

import markdown
import bleach

from app.services.file_service import FileService
from app.services.ocr_service import OCRService
from app.services.ai_service import AIService

from app.prompts.lab_prompt import LAB_PROMPT


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

    def _extract_structured_results(self, analysis_text: str):
        match = JSON_BLOCK_PATTERN.search(analysis_text)

        if not match:
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

    async def process(self, files: list[tuple[bytes, str]], on_stage=None):
        """
        files: لیستی از (بایت‌های فایل, نام اصلی فایل).
        یک یا چند فایل پشتیبانی می‌شود؛ OCR روی همه‌ی فایل‌ها به‌صورت
        هم‌زمان (parallel) انجام و متن‌ها ترکیب می‌شوند، سپس یک
        فراخوانی واحد به AI برای تحلیل ارسال می‌شود.
        """

        total_start = time.perf_counter()

        print("=" * 50)
        print("START REPORT PROCESS")
        print(f"FILE COUNT: {len(files)}")
        print("=" * 50)

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
            }

        limited_text = text[:12000]
        prompt = LAB_PROMPT.format(limited_text)
        print(f"PROMPT LENGTH: {len(prompt)}", flush=True)

        self._notify(on_stage, "ai")

        step_start = time.perf_counter()
        raw_analysis = await self.ai.analyze(prompt)
        ai_duration = time.perf_counter() - step_start
        print(f"AI DONE  [{ai_duration:.2f}s]", flush=True)

        narrative_text, structured_results = self._extract_structured_results(raw_analysis)

        print(f"[ReportService] Extracted {len(structured_results)} structured test result(s)", flush=True)

        analysis_html = self._to_html(narrative_text)

        total_duration = time.perf_counter() - total_start
        print("=" * 50)
        print(f"TOTAL TIME: {total_duration:.2f}s  (OCR: {ocr_duration:.2f}s | AI: {ai_duration:.2f}s)")
        print("=" * 50)

        self._notify(on_stage, "done")

        return {
            "filename": display_filename,
            "ocr": text,
            "analysis": narrative_text,
            "analysis_html": analysis_html,
            "structured_results": structured_results,
        }