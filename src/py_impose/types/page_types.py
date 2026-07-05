import pymupdf


class Rect(pymupdf.Rect):
    def copy(self):
        return Rect(self)

class Tile:
    def __init__(self, page: pymupdf.Page):
        self._page = page

    @property
    def page(self) -> pymupdf.Page:
        return self._page

    @property
    def rect(self) -> Rect:
        return self._page.mediabox

    @property
    def bleed(self) -> pymupdf.Rect:
        return self._page.bleedbox

    @property
    def trim(self) -> pymupdf.Rect:
        return self._page.trimbox

    @property
    def rect_with_bleed(self) -> pymupdf.Rect:
        return self._page.bleedbox
