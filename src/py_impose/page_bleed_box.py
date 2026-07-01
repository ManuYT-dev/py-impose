import pymupdf
from src.py_impose.types.paper_types import PageSize
from .page_resizer import PageResizer


class PageBleedBox:
    def __init__(self, page: pymupdf.Page, doc: pymupdf.Document, default_bleed_pt: float = PageSize.cm_to_points(5)):
        self.page = page
        self.doc = doc
        self.default_bleed_pt = default_bleed_pt
        self._ensure_bleedbox()

    def _has_explicit_bleedbox(self) -> bool:
        raw = self.doc.xref_object(self.page.xref, compressed=False)
        return "BleedBox" in raw

    def _scale_page_content(self):
        trim = self.page.trimbox
        bleed = self.default_bleed_pt

        new_w = trim.width + 2 * bleed
        new_h = trim.height + 2 * bleed

        self.page = PageResizer(PageSize(width=int(round(new_w)), height=int(round(new_h)))).resize_page(
            self.page)

        doc = self.page.parent
        media = self.page.mediabox  # exakte MediaBox nach Resize

        new_trim = pymupdf.Rect(
            bleed * (media.width / new_w),
            bleed * (media.height / new_h),
            media.width - bleed * (media.width / new_w),
            media.height - bleed * (media.height / new_h),
        )

        # BleedBox = exakt die MediaBox
        doc.xref_set_key(self.page.xref, "BleedBox",
                         f"[{media.x0} {media.y0} {media.x1} {media.y1}]")
        doc.xref_set_key(self.page.xref, "TrimBox",
                         f"[{new_trim.x0} {new_trim.y0} {new_trim.x1} {new_trim.y1}]")
        doc.xref_set_key(self.page.xref, "CropBox", "null")
        doc.xref_set_key(self.page.xref, "ArtBox", "null")

    def _ensure_bleedbox(self):
        if not self._has_explicit_bleedbox():
            self._scale_page_content()

    def get_bleedbox(self) -> pymupdf.Rect:
        return self.page.bleedbox