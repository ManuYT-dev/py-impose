from __future__ import annotations
import pymupdf
from .types import BindingType, PageSize, Rect

import logging
logger = logging.getLogger(__name__)


class PageImposer:
    """Reorders and merges single pages into printer-ready spreads/sheets,
    depending on the binding type (book, flyer, ...).
    """

    def __init__(
        self,
        binding: BindingType = BindingType.NORMAL,
        pages_per_sheet: int = 2,
        fold_style: str = "accordion",   # "accordion" | "letter" - only used for FLYER
        panel_shrink: float = PageSize.mm_to_points(2),  # only used for FLYER + "letter"
        has_fold_margin: bool = False,
    ):
        self.binding = binding
        self.pages_per_sheet = pages_per_sheet
        self.fold_style = fold_style
        self.panel_shrink = panel_shrink
        self.has_fold_margin = has_fold_margin

    def impose_pages(self, pages: list[pymupdf.Page]) -> list[pymupdf.Page]:
        if not pages:
            logger.warning("[PageImposer] impose_pages received an empty page list.")
            return []

        if self.binding == BindingType.NORMAL:
            return pages

        try:
            if self.binding == BindingType.BOOK:
                pages = self._pad_to_multiple(pages, 4)
                return self._impose_book(pages)

            if self.binding == BindingType.FLYER:
                pages = self._pad_to_multiple(pages, self.pages_per_sheet)
                return self._impose_flyer(pages)

            logger.error(f"[PageImposer] Unknown binding type: {self.binding}")
            return pages
        except Exception as e:
            logger.error(f"[PageImposer] impose_pages failed: {e}")
            return pages

    def _pad_to_multiple(self, pages: list[pymupdf.Page], multiple: int) -> list[pymupdf.Page]:
        remainder = len(pages) % multiple
        if remainder == 0:
            return pages

        missing = multiple - remainder
        logger.warning(
            f"[PageImposer] Page count {len(pages)} is not a multiple of "
            f"{multiple} — padding with {missing} blank page(s)."
        )

        last = pages[-1]
        blanks: list[pymupdf.Page] = []
        for _ in range(missing):
            blank_doc = pymupdf.open()
            blank_page: pymupdf.Page = blank_doc.new_page(width=last.rect.width, height=last.rect.height)
            self._copy_boxes(last, blank_page)
            blanks.append(blank_page)
        return pages + blanks

    def _copy_boxes(self, source: pymupdf.Page, target: pymupdf.Page) -> None:
        """Blank filler pages need the same BleedBox/TrimBox as the real
        page they're padding next to. Otherwise, whichever side of a
        spread a blank page lands on gets 0 inherited bleed while the
        real content side gets the actual value - which is exactly the
        "one edge is right, the other isn't" asymmetry this fixes.
        """
        if not self._has_explicit_bleedbox(source):
            return  # source had no real bleed data either - nothing to copy

        doc = target.parent
        b, t = source.bleedbox, source.trimbox
        doc.xref_set_key(target.xref, "BleedBox", f"[{b.x0} {b.y0} {b.x1} {b.y1}]")
        doc.xref_set_key(target.xref, "TrimBox", f"[{t.x0} {t.y0} {t.x1} {t.y1}]")

    def _impose_book(self, pages: list[pymupdf.Page]) -> list[pymupdf.Page]:
        """Every physical sheet carries 4 logical pages (2 per side),
        arranged in reader order so that after folding once and
        stapling, page numbers run in sequence.
        """
        n = len(pages)
        sheets = n // 4
        if n % 4 != 0:
            raise ValueError(
                f"[PageImposer] Simple saddle-stitch needs a page count that's "
                f"a multiple of 4, got {n}."
            )

        merged: list[pymupdf.Page] = []
        for k in range(sheets):
            front_left = pages[n - 1 - 2 * k]
            front_right = pages[2 * k]
            back_left = pages[2 * k + 1]
            back_right = pages[n - 2 - 2 * k]

            merged.append(self._merge_panels([front_left, front_right]))
            merged.append(self._merge_panels([back_left, back_right]))

        logger.info(f"[PageImposer] Imposed {n} pages into {len(merged)} book spread(s).")
        return merged

    def _impose_flyer(self, pages: list[pymupdf.Page]) -> list[pymupdf.Page]:
        merged: list[pymupdf.Page] = []
        for i in range(0, len(pages), self.pages_per_sheet):
            group = pages[i:i + self.pages_per_sheet]
            merged.append(self._merge_panels(group))

        logger.info(f"[PageImposer] Imposed {len(pages)} pages into {len(merged)} flyer sheet(s).")
        return merged

    def _merge_panels(self, panels: list[pymupdf.Page]) -> pymupdf.Page:
        """Places N pages side by side onto one new page, left to right."""
        widths = [self._panel_width(idx, len(panels), p) for idx, p in enumerate(panels)]
        total_w = sum(widths)
        total_h = max(p.rect.height for p in panels)

        result = pymupdf.open()
        new_page = result.new_page(width=total_w, height=total_h)
        distances = [self._bleed_distances(p) for p in panels]

        x = 0.0
        for panel, w in zip(panels, widths):
            rect = Rect(x, 0, x + w, total_h)
            clip = self._panel_clip(panel, w)
            new_page.show_pdf_page(rect, panel.parent, panel.number, clip=clip)
            x += w

        self._apply_inherited_bleed(new_page, distances, total_w, total_h)
        return new_page

    def _panel_clip(self, page: pymupdf.Page, target_width: float) -> pymupdf.Rect:
        full = page.rect
        shrink = full.width - target_width
        if shrink <= 0:
            return full

        return Rect(full.x0, full.y0, full.x1 - shrink, full.y1)

    def _has_explicit_bleedbox(self, page: pymupdf.Page) -> bool:
        raw = page.parent.xref_object(page.xref, compressed=False)
        return "BleedBox" in raw

    def _bleed_distances(self, page: pymupdf.Page) -> dict[str, float] | None:
        """Returns how far the page's TrimBox and BleedBox each sit inset
        from its MediaBox on every side, or None if this page never had
        an explicit BleedBox to begin with.
        """
        if not self._has_explicit_bleedbox(page):
            return None

        media = page.rect
        trim = page.trimbox
        bleed = page.bleedbox
        return {
            "trim_left": trim.x0 - media.x0,
            "trim_right": media.x1 - trim.x1,
            "trim_top": trim.y0 - media.y0,
            "trim_bottom": media.y1 - trim.y1,
            "bleed_left": bleed.x0 - media.x0,
            "bleed_right": media.x1 - bleed.x1,
            "bleed_top": bleed.y0 - media.y0,
            "bleed_bottom": media.y1 - bleed.y1,
        }

    def _apply_inherited_bleed(
            self,
            merged_page: pymupdf.Page,
            distances: list[dict[str, float] | None],
            total_w: float,
            total_h: float,
    ) -> None:
        """Sets BleedBox/TrimBox on the merged sheet from the source
        panels' real bleed distances, if any of them had one.
        """
        if not any(distances):
            return

        bleed_left = distances[0]["bleed_left"] if distances[0] else 0.0
        bleed_right = distances[-1]["bleed_right"] if distances[-1] else 0.0
        bleed_top = max((d["bleed_top"] for d in distances if d), default=0.0)
        bleed_bottom = max((d["bleed_bottom"] for d in distances if d), default=0.0)

        outer_left = distances[0]["trim_left"] if distances[0] else 0.0
        outer_right = distances[-1]["trim_right"] if distances[-1] else 0.0
        top = max((d["trim_top"] for d in distances if d), default=0.0)
        bottom = max((d["trim_bottom"] for d in distances if d), default=0.0)

        trim = Rect(outer_left, top, total_w - outer_right, total_h - bottom)
        bleed = Rect(bleed_left, bleed_top, total_w - bleed_right, total_h - bleed_bottom)
        doc = merged_page.parent
        doc.xref_set_key(merged_page.xref, "BleedBox",
                          f"[{bleed.x0} {bleed.y0} {bleed.x1} {bleed.y1}]")
        doc.xref_set_key(merged_page.xref, "TrimBox",
                          f"[{trim.x0} {trim.y0} {trim.x1} {trim.y1}]")

    def _panel_width(self, index: int, count: int, page: pymupdf.Page) -> float:
        base_width = page.rect.width
        if (
            self.binding == BindingType.FLYER
            and self.fold_style == "letter"
            and index == count - 2
            and not self.has_fold_margin
        ):
            return base_width - self.panel_shrink
        return base_width
