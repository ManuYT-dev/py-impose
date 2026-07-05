from __future__ import annotations
import pymupdf
from pathlib import Path
from io import BytesIO

from .types import PageSize, PaperTypes, BindingType
from .page_bleed_box import PageBleedBox
from .page_resizer import PageResizer
from .page_imposer import PageImposer
from .page_tiler import PageTiler
from .pdf_exporter import PDFExporter
from .file_loader import FileLoader

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
            bindung: BindingType = BindingType.NORMAL,
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.tile_to = tile_to
        self.resize_to = resize_to
        self.bindung = bindung
        self.pages: list[pymupdf.Page] = []

        self._load_kwargs = {}
        self._resize_kwargs = {}
        self._impose_kwargs = {}
        self._bleed_kwargs = {}
        self._tile_kwargs = {}
        self._export_kwargs = {}

    def update_value(self, **kwargs) -> "PDFProcessor":
        mapping = {
            "load": self._load_kwargs,
            "resize": self._resize_kwargs,
            "impose": self._impose_kwargs,
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
            img_quality = self._get_with_log(self._load_kwargs, "image_quality", 85)
            img_optimize = self._get_with_log(self._load_kwargs, "optimize_images", True)

            loader = FileLoader(
                self.input_path,
                image_quality=img_quality,
                optimize_images=img_optimize
            )

            self.pages = loader.load(
                self._get_with_log(self._load_kwargs, "start"),
                self._get_with_log(self._load_kwargs, "end"),
                self._get_with_log(self._load_kwargs, "steps")
            )
            if not self.pages:
                logger.warning("[PDFProcessor] load: no pages were loaded.")
        except Exception as e:
            logger.error("[PDFProcessor] load failed: %s", e)
        return self

    def resize(self, **kwargs) -> "PDFProcessor":
        self._resize_kwargs = kwargs or self._resize_kwargs
        size = self._get_with_log(self._resize_kwargs, "size", self.resize_to)

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

    def impose(self, **kwargs) -> "PDFProcessor":
        self._impose_kwargs = kwargs or self._impose_kwargs
        if not self.pages:
            logger.warning("[PDFProcessor] impose: no pages to process.")
            return self
        try:
            binding = self._get_with_log(self._impose_kwargs, "binding", self.bindung or BindingType.NORMAL)
            if isinstance(binding, str):
                binding = BindingType(binding.lower())

            imposer = PageImposer(
                binding=binding,
                pages_per_sheet=self._get_with_log(self._impose_kwargs, "pages_per_sheet", 2),
                fold_style=self._get_with_log(self._impose_kwargs, "fold_style", "accordion"),
                panel_shrink=self._get_with_log(self._impose_kwargs, "panel_shrink", PageSize.mm_to_points(2)),
            )
            self.pages = imposer.impose_pages(self.pages)
        except Exception as e:
            logger.error(f"[PDFProcessor] impose failed: {e}")
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

                bleed_val = self._get_with_log(self._bleed_kwargs, "default_bleed", PageSize.mm_to_points(5))
                scale_val = self._get_with_log(self._bleed_kwargs, "scaleForBleed", True)
                pb = PageBleedBox(page, doc, bleed_val, scale_val)

                new_pages.append(pb.page)  # write back new page
            self.pages = new_pages
        except Exception as e:
            logger.error("[PDFProcessor] bleed failed: %s", e)
        return self

    def tile(self, **kwargs) -> "PDFProcessor":
        self._tile_kwargs = kwargs or self._tile_kwargs

        if not self.pages:
            return self
        try:
            output_size = self._get_with_log(self._tile_kwargs, "output_size", self.tile_to)
            tiler = PageTiler(
                output_size,
                inner_spacing=self._get_with_log(self._tile_kwargs, "inner_spacing"),
                outer_margin=self._get_with_log(self._tile_kwargs, "outer_margin"),
                line_thickness=self._get_with_log(self._tile_kwargs, "line_thickness"),
                draw_lines=self._get_with_log(self._tile_kwargs, "draw_lines", True)
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
            exporter.write(self._get_with_log(self._export_kwargs, "output_path", self.output_path))
        except Exception as e:
            logger.error("[PDFProcessor] export failed: %s", e)
        return self

    def run(self) -> "PDFProcessor":
        """Run the full processing pipeline using any pre-configured settings."""
        logger.info("[PDFProcessor] Starting pipeline for '%s'", self.input_path)
        return self.load().resize().impose().bleed().tile().export()

    @staticmethod
    def _get_with_log(data: dict, key: str, default: any = None) -> any:
        """Gets a value out of a dict, or logs an error if the key does not exist."""
        if key not in data:
            logger.warning("[PDFProcessor] No value found, using default for '%s'", key)
            return default
        return data.get(key)
