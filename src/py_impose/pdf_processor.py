class PDFProcessor:
    """High level pipeline for loading, resizing, tiling and exporting PDFs."""

    def __init__(
            self,
            input_path: str | Path | BytesIO,
            output_path: str | Path,
            tile_to: paper_types.PageSize = paper_types.SRA3,
            resize_to: paper_types.PageSize | None = None,
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
    #  Factory                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_auftrag(
            cls,
            auftrag: Auftrag,
            email: Email,
            output_path: str | Path,
            tile_to: paper_types.PageSize = paper_types.SRA3,
    ) -> "PDFProcessor | None":
        """Erstellt einen PDFProcessor direkt aus einem Auftrag und der zugehörigen Email.

        Returns None wenn kein passender Anhang gefunden wurde.
        """
        attachment: Attachment | None = email.get_attachment_for(auftrag)
        if attachment is None or attachment.page_size(0) is None:
            logger.error(
                "[PDFProcessor] from_auftrag: no attachment found for '%s'",
                auftrag.Dateiname,
            )
            return None

        # Berechnung welches A format man hat mit Schutz, falls width größer height ist
        page_size = attachment.page_size(0)
        temp_size = paper_types.PageSize(min(page_size.to_list()), max(page_size.to_list()))
        name, dist = paper_types.find_closest_size(temp_size)

        return cls(
            input_path=attachment.as_stream(),
            output_path=output_path,
            tile_to=tile_to,
            resize_to=paper_types.Paper_Sizes.get(auftrag.Papier_Groeße, paper_types.Paper_Sizes[name]),
            anzahl=auftrag.Anzahl,
            farbe=auftrag.Farbe,
            beidseitig=auftrag.Beidseitig,
            bindung=auftrag.Bindung,
        )

    @classmethod
    def from_email(
            cls,
            email: Email,
            output_dir: str | Path,
            tile_to: paper_types.PageSize = paper_types.SRA3,
    ) -> list["PDFProcessor"]:
        """Erstellt einen PDFProcessor pro Auftrag in der Email."""
        output_dir = Path(output_dir)
        processors = []
        for auftrag in email.Auftraege:
            output_path = output_dir / f"{Path(auftrag.Dateiname or 'output').stem}_tiled.pdf"
            processor = cls.from_auftrag(auftrag, email, output_path, tile_to)
            if processor:
                processors.append(processor)
        return processors

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
                pb = PageBleedBox(page, doc, self._bleed_kwargs.get("default_bleed_pt", paper_types.PageSize.mm_to_points(5)))
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
                inner_spacing=self._tile_kwargs.get("inner_spacing"),
                outer_margin=self._tile_kwargs.get("outer_margin"),
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
