from __future__ import annotations
from enum import Enum
from collections.abc import Iterable
import math


class PageSize:
    """Encapsulates page sizes and conversions."""
    def __init__(self, width: float | Iterable[float], height: float | None = None) -> None:
        if height is None and isinstance(width, Iterable) and not isinstance(width, (str, bytes)):
            values = list(width)

            if len(values) != 2:
                raise ValueError("Iterable must contain exactly two values: (width, height)")

            self.width = values[0]
            self.height = values[1]

        else:
            if not isinstance(width, float | int) or height is None:
                raise ValueError("Width and height must both be floats.")

            self.width = width
            self.height = height

    @staticmethod
    def cm_to_points(cm: float):
        return cm * 28.3464567

    @staticmethod
    def mm_to_points(mm: float):
        return mm * 2.83464567

    @classmethod
    def from_cm(cls, w_cm, h_cm):
        return cls(width=PageSize.cm_to_points(w_cm), height=PageSize.cm_to_points(h_cm))

    @classmethod
    def from_mm(cls, w_mm, h_mm):
        return cls(width=PageSize.mm_to_points(w_mm), height=PageSize.mm_to_points(h_mm))

    def to_list(self):
        return [self.width, self.height]

    def find_closest_size(self):
        best_match = None
        min_distance = float('inf')

        t_w, t_h = sorted([self.width, self.height])

        for name, value in PaperTypes:
            s_w, s_h = sorted([value.width, value.height])

            # Euklidische Distanz berechnen
            distance = math.sqrt((t_w - s_w) ** 2 + (t_h - s_h) ** 2)

            if distance < min_distance:
                min_distance = distance
                best_match = name

        return best_match, min_distance


class PaperTypes(Enum):
    A0 = PageSize(2384, 3370)
    A1 = PageSize(1684, 2384)
    A2 = PageSize(1191, 1684)
    SRA3 = PageSize(907, 1276)
    A3 = PageSize(842, 1191)
    A4 = PageSize(595, 842)
    A5 = PageSize(420, 595)
    A6 = PageSize(298, 420)
    A7 = PageSize(210, 298)
    A8 = PageSize(147, 210)