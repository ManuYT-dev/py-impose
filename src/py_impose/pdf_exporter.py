from __future__ import annotations
import pymupdf
from pathlib import Path

import logging
logger = logging.getLogger(__name__)


class PDFExporter:
    """Exports processed pages to a new PDF document."""

    def __init__(self):
        self.output_document = pymupdf.open()

    def clear_pages(self):
        try:
            if self.output_document is not None and self.output_document.page_count > 0:
                self.output_document.delete_pages(0, self.output_document.page_count - 1)
            else:
                logger.warning("[PDFExporter] clear_pages: The document to clear the pages from either doesnt exist or has no pages")
        except AttributeError:
            logger.error("[PDFExporter] clear_pages: invalid page object.")
        except Exception as e:
            logger.error(f"[PDFExporter] clear_pages: failed to clear: {e}")

    def add_page(self, page: pymupdf.Page) -> None:
        try:
            self.output_document.insert_pdf(page.parent, from_page=page.number, to_page=page.number)
        except AttributeError:
            logger.error("[PDFExporter] add_page: invalid page object.")
        except Exception as e:
            logger.error(f"[PDFExporter] add_page failed for page {getattr(page, 'number', '?')}: {e}")

    def add_pages(self, pages: list[pymupdf.Page]) -> None:
        if not pages:
            logger.warning("[PDFExporter] add_pages received an empty page list.")
            return
        for page in pages:
            self.add_page(page)
        logger.info(f"[PDFExporter] Added {len(pages)} pages to output document.")

    def write(self, file_path: str | Path) -> None:
        try:
            self.output_document.save(file_path)
            logger.info(f"[PDFExporter] Saved output PDF to '{file_path}'")
        except PermissionError:
            logger.error(f"[PDFExporter] Permission denied writing to '{file_path}'.")
        except Exception as e:
            logger.error(f"[PDFExporter] Failed to save PDF to '{file_path}': {e}")
