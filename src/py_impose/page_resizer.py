from __future__ import annotations
import pymupdf
from .types import PageSize, Rect

import logging
logger = logging.getLogger(__name__)


class PageResizer:
    """Resizes individual pages to match a target paper size."""

    def __init__(self, target_size: PageSize):
        try:
            self.target_width = float(target_size.width)
            self.target_height = float(target_size.height)
        except (AttributeError, TypeError, ValueError) as e:
            logger.error(f"[PageResizer] Invalid target_size: {e}")
            self.target_width = 0.0
            self.target_height = 0.0

    def resize_page(self, page: pymupdf.Page) -> pymupdf.Page | None:
        try:
            raw = page.parent.xref_object(page.xref, compressed=False)
            has_bleed = "BleedBox" in raw
            has_trim = "TrimBox" in raw

            source_rect = page.bleedbox if has_bleed else page.rect

            # Check if the source page is landscape
            source_is_landscape = source_rect.width > source_rect.height
            # Check if the target is defined as landscape
            target_is_landscape = self.target_width > self.target_height

            if source_is_landscape != target_is_landscape:
                current_target_w = self.target_height
                current_target_h = self.target_width
            else:
                current_target_w = self.target_width
                current_target_h = self.target_height

            # Skalierung relativ zur source_rect
            scale_x = current_target_w / source_rect.width
            scale_y = current_target_h / source_rect.height

            result = pymupdf.open()
            new_page = result.new_page(width=current_target_w, height=current_target_h)

            new_page.show_pdf_page(
                Rect(0, 0, current_target_w, current_target_h),
                page.parent, page.number,
                clip=source_rect,
                keep_proportion=False
            )

            # BleedBox = gesamte neue Seite
            if has_bleed:
                result.xref_set_key(new_page.xref, "BleedBox",
                                    f"[0 0 {current_target_w} {current_target_h}]")

            # TrimBox relativ zur BleedBox (source_rect) neu berechnen
            if has_trim:
                trim = page.trimbox
                new_trim = Rect(
                    (trim.x0 - source_rect.x0) * scale_x,
                    (trim.y0 - source_rect.y0) * scale_y,
                    (trim.x1 - source_rect.x0) * scale_x,
                    (trim.y1 - source_rect.y0) * scale_y,
                )
                # Sicherstellen dass TrimBox innerhalb der MediaBox bleibt
                new_trim = new_trim & Rect(0, 0, current_target_w, current_target_h)
                result.xref_set_key(new_page.xref, "TrimBox",
                                    f"[{new_trim.x0} {new_trim.y0} {new_trim.x1} {new_trim.y1}]")

            return new_page
        except AttributeError:
            logger.error("[PageResizer] Invalid page object passed to resize_page.")
            return None
        except Exception as e:
            logger.error(f"[PageResizer] Failed to resize page {getattr(page, 'number', '?')}: {e}")
            return None

    def resize_pages(self, pages: list[pymupdf.Page]) -> list[pymupdf.Page]:
        if not pages:
            logger.warning("[PageResizer] resize_pages received an empty page list.")
            return []

        resized = [self.resize_page(p) for p in pages]
        failed = resized.count(None)
        result = [p for p in resized if p is not None]

        if failed:
            logger.warning(f"[PageResizer] {failed} page(s) failed to resize and were skipped.")

        logger.info(f"[PageResizer] Resized {len(result)} of {len(pages)} pages.")
        return result
