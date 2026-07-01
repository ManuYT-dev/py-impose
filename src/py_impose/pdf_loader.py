from __future__ import annotations
import pymupdf
from pathlib import Path
from io import BytesIO

import logging
logger = logging.getLogger(__name__)


class PDFLoader:
    """Loads PDF files and extracts individual pages using PyMuPDF."""

    def __init__(self, file_path: str | Path | BytesIO):
        self.file_path = file_path
        self.document: pymupdf.Document | None = None

    def load(self, start=None, stop=None, step=None) -> list[pymupdf.Page]:
        try:
            if isinstance(self.file_path, BytesIO):
                self.document = pymupdf.Document(stream=self.file_path)
            else:
                self.document = pymupdf.Document(filename=self.file_path)
        except FileNotFoundError:
            logger.error(f"[PDFLoader] File not found: '{self.file_path}'")
            return []
        except pymupdf.FileDataError:
            logger.error(f"[PDFLoader] File is not a valid PDF: '{self.file_path}'")
            return []
        except Exception as e:
            logger.error(f"[PDFLoader] Unexpected error opening '{self.file_path}': {e}")
            return []

        try:
            pages = list(self.document.pages(start=start, stop=stop, step=step))
            logger.info(f"[PDFLoader] Loaded {len(pages)} pages from '{self.file_path}'")
            return pages
        except ValueError as e:
            logger.error(f"[PDFLoader] Invalid page range (start={start}, stop={stop}, step={step}): {e}")
            return []
        except Exception as e:
            logger.error(f"[PDFLoader] Unexpected error reading pages: {e}")
            return []
