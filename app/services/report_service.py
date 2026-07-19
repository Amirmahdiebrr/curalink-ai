import time
import json
import re

import markdown

from app.services.file_service import FileService
from app.services.ocr_service import OCRService
from app.services.ai_service import AIService

from app.prompts.lab_prompt import LAB_PROMPT


JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\[.*?\])\s*```", re.DOTALL)


class ReportService:

    def __init__(self):
        self.file_service = FileService()
        self.ocr = OCRService()
        self.ai = AIService()

    def _to_html(self, text: str) -> str:
        return markdown.markdown(
            text,
            extensions=["extra", "nl2br", "sane_lists"]
        )

    def _extract_structured_results(self, analysis_text: str):
        """
        Finds the trailing ```json [...] ``` block in the AI response,
        parses it, and returns (narrative_text_without_json, structured_list).
        On any parsing failure, returns the original text unchanged and
        an empty structured list, so the narrative report is never broken.
        """

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

    async def process(self, content: bytes, filename: str, on_stage=None):

        total_start = time.perf_counter()

        print("=" * 50)
        print("START REPORT PROCESS")
        print("=" * 50)

        self._notify(on_stage, "saving")

        step_start = time.perf_counter()
        filepath = self.file_service.save_bytes(filename, content)
        print(f"FILE SAVED: {filepath}  [{time.perf_counter() - step_start:.2f}s]", flush=True)

        self._notify(on_stage, "ocr")

        step_start = time.perf_counter()
        try:
            text = await self.ocr.extract(filepath)
        except Exception as e:
            print(f"[ReportService] OCR error: {e}  [{time.perf_counter() - step_start:.2f}s]", flush=True)
            error_html = self._to_html(f"**خطا در OCR:** {e}")
            return {
                "filename": filepath.name,
                "ocr": "",
                "analysis": "",
                "analysis_html": error_html,
                "structured_results": [],
            }

        ocr_duration = time.perf_counter() - step_start
        print(f"OCR DONE  [{ocr_duration:.2f}s]", flush=True)
        print(f"OCR LENGTH: {len(text)}", flush=True)

        if not text.strip():
            print("[ReportService] OCR returned empty text", flush=True)
            error_html = self._to_html(
                "متنی از فایل استخراج نشد. لطفاً تصویر واضح‌تری آپلود کنید."
            )
            return {
                "filename": filepath.name,
                "ocr": text,
                "analysis": "",
                "analysis_html": error_html,
                "structured_results": [],
            }

        limited_text = text[:4000]
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
            "filename": filepath.name,
            "ocr": text,
            "analysis": narrative_text,
            "analysis_html": analysis_html,
            "structured_results": structured_results,
        }