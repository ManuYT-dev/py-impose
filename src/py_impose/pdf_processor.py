from __future__ import annotations
import pymupdf
from pathlib import Path
from io import BytesIO

from .types import PageSize, PaperTypes
from .page_bleed_box import PageBleedBox
from .page_resizer import PageResizer
from .page_tiler import PageTiler
from .pdf_exporter import PDFExporter
from .pdf_loader import PDFLoader

import logging
logger = logging.getLogger(__name__)


class PDFProcessor:
    """High level pipeline for loading, resizing, tiling and exporting PDFs."""

    def __init__(
            self,
            input_path: str | Path | BytesIO,
            output_path: str | Path,
            tile_to: PageSize = PaperTypes.SRA3,
            resize_to: PageSize | None = None,
            anzahl: int = 1,
            farbe: bool = False,
            beidseitig: bool = False,
            bindung: str | None = None,
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.tile_to = tile_to
        self.resize_to = resize_to
        self.anzahl = anzahl
        self.farbe = farbe
        self.beidseitig = beidseitig
        self.bindung = bindung
        self.pages: list[pymupdf.Page] = []

        self._load_kwargs = {}
        self._resize_kwargs = {}
        self._bleed_kwargs = {}
        self._tile_kwargs = {}
        self._export_kwargs = {}

    # ------------------------------------------------------------------ #
    #  Pipeline                                                            #
    # ------------------------------------------------------------------ #

    def update_value(self, **kwargs) -> "PDFProcessor":
        mapping = {
            "load": self._load_kwargs,
            "resize": self._resize_kwargs,
            "bleed": self._bleed_kwargs,
            "tile": self._tile_kwargs,
            "export": self._export_kwargs,
        }
        for key, value in kwargs.items():
            # z.B. resize__size=paper_types.A4
            if "__" in key:
                group, subkey = key.split("__", 1)
                if group in mapping:
                    mapping[group][subkey] = value
                else:
                    logger.error("[PDFProcessor] update_value: unknown group '%s' — skipped.", group)
            elif hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.error("[PDFProcessor] update_value: unknown attribute '%s' — skipped.", key)
        return self

    def load(self, **kwargs) -> "PDFProcessor":
        self._load_kwargs = kwargs or self._load_kwargs
        try:
            self.pages = PDFLoader(self.input_path).load(
                self._load_kwargs.get("start"),
                self._load_kwargs.get("end"),
                self._load_kwargs.get("steps"),
            )
            if not self.pages:
                logger.warning("[PDFProcessor] load: no pages were loaded.")
        except Exception as e:
            logger.error("[PDFProcessor] load failed: %s", e)
        return self

    def resize(self, **kwargs) -> "PDFProcessor":
        self._resize_kwargs = kwargs or self._resize_kwargs
        size = self._resize_kwargs.get("size") or self.resize_to

        if size is None:
            return self

        if not self.pages:
            logger.warning("[PDFProcessor] resize: no pages to resize.")
            return self

        try:
            self.pages = PageResizer(size).resize_pages(self.pages)
        except Exception as e:
            logger.error("[PDFProcessor] resize failed: %s", e)
        return self

    def bleed(self, **kwargs) -> "PDFProcessor":
        self._bleed_kwargs = kwargs or self._bleed_kwargs

        if not self.pages:
            logger.warning("[PDFProcessor] bleed: no pages to process.")
            return self

        try:
            new_pages = []
            for page in self.pages:
                doc = page.parent
                pb = PageBleedBox(page, doc, self._bleed_kwargs.get("default_bleed_pt", PageSize.mm_to_points(5)))
                new_pages.append(pb.page)  # neue Page zurückschreiben
            self.pages = new_pages
        except Exception as e:
            logger.error("[PDFProcessor] bleed failed: %s", e)
        return self

    def tile(self, **kwargs) -> "PDFProcessor":
        self._tile_kwargs = kwargs or self._tile_kwargs

        if not self.pages:
            return self
        try:
            output_size = self._tile_kwargs.get("output_size") or self.tile_to
            tiler = PageTiler(
                output_size,
                inner_spacing_mm=self._tile_kwargs.get("inner_spacing_mm"),
                outer_margin_mm=self._tile_kwargs.get("outer_margin_mm"),
                line_thickness=self._tile_kwargs.get("line_thickness"),
                draw_lines=self._tile_kwargs.get("draw_lines", True)
            )
            self.pages = tiler.tile_pages(
                self.pages,
            )
        except Exception as e:
            logger.error("[PDFProcessor] tile failed: %s", e)
        return self

    def export(self, **kwargs) -> "PDFProcessor":
        self._export_kwargs = kwargs or self._export_kwargs

        if not self.pages:
            logger.warning("[PDFProcessor] export: no pages to export.")
            return self

        try:
            exporter = PDFExporter()
            exporter.add_pages(self.pages)
            exporter.write(self._export_kwargs.get("output_path") or self.output_path)
        except Exception as e:
            logger.error("[PDFProcessor] export failed: %s", e)
        return self

    def run(self) -> "PDFProcessor":
        """Run the full processing pipeline using any pre-configured settings."""
        logger.info("[PDFProcessor] Starting pipeline for '%s'", self.input_path)
        return self.load().resize().bleed().tile().export()

    def __repr__(self):
        return (
            f"PDFProcessor(input={self.input_path}, anzahl={self.anzahl}, "
            f"farbe={self.farbe}, beidseitig={self.beidseitig})"
        )
