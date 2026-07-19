"""
app/services/ocr_service.py

OCR service for extracting text from medical documents using
NVIDIA's hosted Nemotron OCR v1 model (cloud-based, GPU-accelerated).
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import httpx
import fitz  # PyMuPDF

from app.config import NVIDIA_API_KEY


NEMOTRON_OCR_URL = "https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v1"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class OCRExtractionError(Exception):
    pass


class OCRService:

    @classmethod
    def _pdf_to_image_bytes(cls, pdf_path: Path) -> list[bytes]:
        images = []
        doc = fitz.open(str(pdf_path))
        try:
            for page in doc:
                matrix = fitz.Matrix(2.5, 2.5)
                pix = page.get_pixmap(matrix=matrix)
                images.append(pix.tobytes("png"))
        finally:
            doc.close()
        return images

    @classmethod
    def _build_data_url(cls, image_bytes: bytes, media_type: str) -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/{media_type};base64,{b64}"

    @classmethod
    async def extract(cls, file_path: Path) -> str:
        return await cls.extract_text(file_path)

    @classmethod
    async def extract_text(cls, file_path: Path) -> str:

        if not file_path.exists():
            raise OCRExtractionError(f"File not found: {file_path}")

        extension = file_path.suffix.lower()

        image_payloads = []

        if extension == ".pdf":
            print("[OCR] PDF detected, converting pages to images...", flush=True)
            t0 = time.perf_counter()
            page_images = cls._pdf_to_image_bytes(file_path)
            print(f"[OCR] {len(page_images)} page(s) extracted from PDF  [{time.perf_counter() - t0:.2f}s]", flush=True)

            for img_bytes in page_images:
                image_payloads.append({
                    "type": "image_url",
                    "url": cls._build_data_url(img_bytes, "png")
                })

        elif extension in (".jpg", ".jpeg", ".png"):
            media_type = "jpeg" if extension in (".jpg", ".jpeg") else "png"
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            image_payloads.append({
                "type": "image_url",
                "url": cls._build_data_url(img_bytes, media_type)
            })

        else:
            raise OCRExtractionError(f"Unsupported file type: {extension}")

        payload = {
            "input": image_payloads,
            "merge_levels": ["paragraph"] * len(image_payloads)
        }

        headers = dict(REQUEST_HEADERS)
        headers["Authorization"] = "Bearer " + NVIDIA_API_KEY

        print(f"[OCR] Sending {len(image_payloads)} image(s) to Nemotron OCR...", flush=True)

        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(NEMOTRON_OCR_URL, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise OCRExtractionError(f"درخواست OCR با تایم‌اوت مواجه شد: {e}") from e
        except Exception as e:
            raise OCRExtractionError(f"درخواست OCR با خطا مواجه شد: {e}") from e

        elapsed = time.perf_counter() - t0

        print(f"[OCR] Nemotron OCR response status: {response.status_code}  [{elapsed:.2f}s]", flush=True)

        if response.status_code != 200:
            raise OCRExtractionError(f"خطای OCR API {response.status_code}: {response.text[:300]}")

        try:
            data = response.json()
        except Exception as e:
            raise OCRExtractionError(f"خطا در خواندن پاسخ OCR: {e}") from e

        pages = sorted(data.get("data", []), key=lambda p: p.get("index", 0))

        all_pages_text = []

        for page in pages:
            detections = page.get("text_detections", [])
            texts = [
                det["text_prediction"]["text"]
                for det in detections
                if det.get("text_prediction", {}).get("text")
            ]
            all_pages_text.append("\n".join(texts))

        full_text = "\n".join(all_pages_text).strip()

        if not full_text:
            raise OCRExtractionError("متنی از تصویر تشخیص داده نشد.")

        print(f"[OCR] Extracted {len(full_text)} characters total", flush=True)

        return full_text