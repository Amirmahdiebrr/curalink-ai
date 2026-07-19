from pathlib import Path

import easyocr

from PIL import Image

import fitz


class OCRService:

    def __init__(self):

        self.reader = easyocr.Reader(
            ["fa", "en"],
            gpu=False,
        )

    def extract(self, filepath: Path):

        suffix = filepath.suffix.lower()

        if suffix == ".pdf":

            return self._pdf(filepath)

        return self._image(filepath)

    def _image(self, filepath):

        result = self.reader.readtext(str(filepath))

        text = ""

        for item in result:

            text += item[1] + "\n"

        return text

    def _pdf(self, filepath):

        doc = fitz.open(filepath)

        text = ""

        for page in doc:

            txt = page.get_text()

            if txt.strip():

                text += txt

            else:

                pix = page.get_pixmap()

                temp = "temp_page.png"

                pix.save(temp)

                text += self._image(Path(temp))

        doc.close()

        return text