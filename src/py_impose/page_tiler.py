from __future__ import annotations
import pymupdf
from .types import PageSize, Tile, Rect

import logging
logger = logging.getLogger(__name__)


class PageTiler:
    """Arranges multiple copies of a page on a single print sheet, automatically selecting the best orientation."""

    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"

    def __init__(self, target_size: PageSize, inner_spacing: float = None,
                 outer_margin: float = None, line_thickness: float = None, draw_lines: bool = True):
        try:
            self.target_width = float(target_size.width)
            self.target_height = float(target_size.height)
        except (AttributeError, TypeError, ValueError) as e:
            logger.error(f"[PageTiler] Invalid target_size: {e}")
            self.target_width = 0.0
            self.target_height = 0.0

        self.inner_spacing = inner_spacing or PageSize.mm_to_points(2)
        self.outer_margin = outer_margin or PageSize.mm_to_points(2)
        self.line_thickness = line_thickness or PageSize.mm_to_points(1)
        self.draw_lines = draw_lines

    def compute_grid(self, width: float, height: float) -> tuple[int, int]:
        try:
            usable_w = self.target_width - 2 * self.outer_margin
            usable_h = self.target_height - 2 * self.outer_margin
            cols = max(0, int((usable_w + self.inner_spacing) // (width + self.inner_spacing)))
            rows = max(0, int((usable_h + self.inner_spacing) // (height + self.inner_spacing)))
            return cols, rows
        except ZeroDivisionError:
            logger.error(f"[PageTiler] compute_grid: tile size is zero (width={width}, height={height}).")
            return 0, 0
        except Exception as e:
            logger.error(f"[PageTiler] compute_grid failed: {e}")
            return 0, 0

    def choose_orientation(self, width: float, height: float) -> tuple[str, tuple[int, int]]:
        try:
            h_grid = self.compute_grid(width,  height)
            v_grid = self.compute_grid(height, width)
            if h_grid[0] * h_grid[1] >= v_grid[0] * v_grid[1]:
                return self.HORIZONTAL, h_grid
            return self.VERTICAL, v_grid
        except Exception as e:
            logger.error(f"[PageTiler] choose_orientation failed: {e}")
            return self.HORIZONTAL, (0, 0)

    def _build_content_page(self, source_page: pymupdf.Page, grid: tuple[int, int],
                            tile: Tile, rotation: int) -> pymupdf.Page | None:
        try:
            cols, rows = grid

            tile_w = tile.rect.height if rotation == 90 else tile.rect.width
            tile_h = tile.rect.width if rotation == 90 else tile.rect.height

            content_w = cols * tile_w + (cols - 1) * self.inner_spacing
            content_h = rows * tile_h + (rows - 1) * self.inner_spacing

            content_page = pymupdf.open().new_page(width=content_w, height=content_h)
            stride_x = tile_w + self.inner_spacing
            stride_y = tile_h + self.inner_spacing

            for row in range(rows):
                for col in range(cols):
                    rect = Rect(
                        col * stride_x,
                        row * stride_y,
                        col * stride_x + tile_w,
                        row * stride_y + tile_h,
                    )
                    content_page.show_pdf_page(
                        rect, source_page.parent, source_page.number, rotate=rotation
                    )
            return content_page
        except Exception as e:
            logger.error(f"[PageTiler] _build_content_page failed: {e}")
            return None

    def _center_on_sheet(self, content_page: pymupdf.Page) -> pymupdf.Page | None:
        try:
            cw, ch = content_page.mediabox.width, content_page.mediabox.height
            ox = (self.target_width - cw) / 2
            oy = (self.target_height - ch) / 2

            final_page = pymupdf.open().new_page(width=self.target_width, height=self.target_height)
            final_page.show_pdf_page(
                Rect(ox, oy, ox + cw, oy + ch),
                content_page.parent,
                content_page.number,
            )
            return final_page
        except Exception as e:
            logger.error(f"[PageTiler] _center_on_sheet failed: {e}")
            return None

    def tile_page(self, page: pymupdf.Page) -> pymupdf.Page | None:
        try:
            orientation, grid = self.choose_orientation(page.rect.width, page.rect.height)

            if grid[0] == 0 or grid[1] == 0:
                logger.warning(f"[PageTiler] Page {page.number} does not fit on the sheet — returning blank page.")
                return pymupdf.open().new_page(width=self.target_width, height=self.target_height)

            rotate = 90 if orientation == self.VERTICAL else 0
            tile = Tile(page)

            content_page = self._build_content_page(page, grid, tile, rotate)
            if content_page is None:
                return None

            finale_page = self._center_on_sheet(content_page)
            if finale_page is None:
                return None

            if self.draw_lines:
                self.draw_center_lines(grid, finale_page, tile, rotate)
                self.draw_corner_marks(grid, finale_page, tile, rotate)

            return finale_page
        except Exception as e:
            logger.error(f"[PageTiler] tile_page failed for page {getattr(page, 'number', '?')}: {e}")
            return None

    def tile_pages(self, pages: list[pymupdf.Page]) -> list[pymupdf.Page]:
        if not pages:
            logger.warning("[PageTiler] tile_pages received an empty page list.")
            return []

        tiled = [self.tile_page(p) for p in pages]
        failed = tiled.count(None)
        result = [p for p in tiled if p is not None]

        if failed:
            logger.warning(f"[PageTiler] {failed} page(s) failed to tile and were skipped.")

        logger.info(f"[PageTiler] Tiled {len(result)} of {len(pages)} pages.")
        return result

    @staticmethod
    def _get_tile_dimensions(tile: Tile, rotation: int) -> tuple[float, float]:
        """Gibt die effektiven Tile-Dimensionen nach Rotation zurück."""
        if rotation == 90:
            return tile.rect.height, tile.rect.width  # getauscht
        return tile.rect.width, tile.rect.height

    def _get_margins(self, grid: tuple[int, int], finale_page: pymupdf.Page, tile: Tile, rotation: int = 0) -> tuple[
        float, float]:
        cols, rows = grid
        tile_w, tile_h = self._get_tile_dimensions(tile, rotation)
        margin_height = (finale_page.mediabox.height - (rows * tile_h + (rows - 1) * self.inner_spacing)) / 2
        margin_width = (finale_page.mediabox.width - (cols * tile_w + (cols - 1) * self.inner_spacing)) / 2
        return margin_width, margin_height

    def draw_corner_marks(self, grid: tuple[int, int], finale_page: pymupdf.Page, tile: Tile,
                          rotation: int = 0) -> None:
        try:
            cols, rows = grid
            margin_width, margin_height = self._get_margins(grid, finale_page, tile, rotation)
            if margin_height <= 0 or margin_width <= 0: return

            sixth_h, sixth_w = margin_height / 6, margin_width / 6
            page_h, page_w = finale_page.mediabox.height, finale_page.mediabox.width
            tile_w, tile_h = self._get_tile_dimensions(tile, rotation)

            if rotation == 90:
                trim_left = tile.trim.y0 - tile.rect.y0
                trim_right = tile.rect.y1 - tile.trim.y1
                trim_top = tile.trim.x0 - tile.rect.x0
                trim_bottom = tile.rect.x1 - tile.trim.x1
            else:
                trim_left = tile.trim.x0 - tile.rect.x0
                trim_right = tile.rect.x1 - tile.trim.x1
                trim_top = tile.trim.y0 - tile.rect.y0
                trim_bottom = tile.rect.y1 - tile.trim.y1

            # Immer beide Seiten zeichnen — auch wenn cols/rows == 1
            for col_idx in [1, cols] if cols > 1 else [1]:
                x_base = margin_width + col_idx * tile_w + (col_idx - 1) * self.inner_spacing
                x_left = x_base - tile_w + trim_left
                x_right = x_base - trim_right

                for x in ([x_left] if col_idx == 1 else []) + ([x_right] if col_idx == cols else []):
                    finale_page.draw_line((x, sixth_h), (x, margin_height - sixth_h),
                                          width=self.line_thickness, color=(0, 0, 0))
                    finale_page.draw_line((x, page_h - margin_height + sixth_h), (x, page_h - sixth_h),
                                          width=self.line_thickness, color=(0, 0, 0))

            # Beide Seiten für rows
            for row_idx in [1, rows] if rows > 1 else [1]:
                y_base = margin_height + row_idx * tile_h + (row_idx - 1) * self.inner_spacing
                y_top = y_base - tile_h + trim_top
                y_bottom = y_base - trim_bottom

                for y in ([y_top] if row_idx == 1 else []) + ([y_bottom] if row_idx == rows else []):
                    finale_page.draw_line((sixth_w, y), (margin_width - sixth_w, y),
                                          width=self.line_thickness, color=(0, 0, 0))
                    finale_page.draw_line((page_w - margin_width + sixth_w, y), (page_w - sixth_w, y),
                                          width=self.line_thickness, color=(0, 0, 0))

        except Exception as e:
            logger.error(f"draw_corner_marks failed: {e}")

    def draw_center_lines(self, grid: tuple[int, int], finale_page: pymupdf.Page, tile: Tile,
                          rotation: int = 0) -> None:
        try:
            cols, rows = grid
            margin_width, margin_height = self._get_margins(grid, finale_page, tile, rotation)
            if margin_height <= 0 or margin_width <= 0: return

            sixth_h, sixth_w = margin_height / 6, margin_width / 6
            page_h, page_w = finale_page.mediabox.height, finale_page.mediabox.width
            tile_w, tile_h = self._get_tile_dimensions(tile, rotation)

            if rotation == 90:
                trim_left = tile.trim.y0 - tile.rect.y0
                trim_top = tile.trim.x0 - tile.rect.x0
            else:
                trim_left = tile.trim.x0 - tile.rect.x0
                trim_top = tile.trim.y0 - tile.rect.y0

            for col in range(1, cols):
                x_right = margin_width + col * tile_w + (col - 1) * self.inner_spacing - trim_left
                x_left_next = margin_width + (col + 1) * tile_w + col * self.inner_spacing - tile_w + trim_left

                for x in [x_right, x_left_next]:
                    finale_page.draw_line((x, sixth_h), (x, margin_height - sixth_h),
                                          width=self.line_thickness, color=(0, 0, 0))
                    finale_page.draw_line((x, page_h - margin_height + sixth_h), (x, page_h - sixth_h),
                                          width=self.line_thickness, color=(0, 0, 0))

            for row in range(1, rows):
                y_bottom = margin_height + row * tile_h + (row - 1) * self.inner_spacing - trim_top
                y_top_next = margin_height + (row + 1) * tile_h + row * self.inner_spacing - tile_h + trim_top

                for y in [y_bottom, y_top_next]:
                    finale_page.draw_line((sixth_w, y), (margin_width - sixth_w, y),
                                          width=self.line_thickness, color=(0, 0, 0))
                    finale_page.draw_line((page_w - margin_width + sixth_w, y), (page_w - sixth_w, y),
                                          width=self.line_thickness, color=(0, 0, 0))

        except Exception as e:
            logger.error(f"draw_center_lines failed: {e}")
