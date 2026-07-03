from __future__ import annotations

from PIL import Image, ImageFile
import pymupdf
from pathlib import Path
from io import BytesIO

import logging
logger = logging.getLogger(__name__)


class FileLoader:
    """Loads PDF files and extracts individual pages using PyMuPDF."""

    def __init__(
        self,
        file_path: str | Path | BytesIO,
        image_quality: int = 85,
        optimize_images: bool = True
    ):
        self.file_path = file_path
        self.document: pymupdf.Document | None = None
        self.image_quality = image_quality
        self.optimize_images = optimize_images

    def load(self, start=None, stop=None, step=None) -> list[pymupdf.Page]:
        self._ensure_correct_format()
        try:
            if isinstance(self.file_path, BytesIO):
                self.document = pymupdf.Document(stream=self.file_path)
            else:
                self.document = pymupdf.Document(filename=self.file_path)
        except FileNotFoundError:
            logger.error(f"[PDFLoader] File not found: '{self.file_path}'")
            return []
        except pymupdf.FileDataError:
            logger.error(f"[PDFLoader] File is not a valid PDF: '{self.file_path}'")
            return []
        except Exception as e:
            logger.error(f"[PDFLoader] Unexpected error opening '{self.file_path}': {e}")
            return []

        try:
            pages = list(self.document.pages(start=start, stop=stop, step=step))
            logger.info(f"[PDFLoader] Loaded {len(pages)} pages from '{self.file_path}'")
            return pages
        except ValueError as e:
            logger.error(f"[PDFLoader] Invalid page range (start={start}, stop={stop}, step={step}): {e}")
            return []
        except Exception as e:
            logger.error(f"[PDFLoader] Unexpected error reading pages: {e}")
            return []

    def _ensure_correct_format(self):
        """Normalizes self.file_path into a PDF BytesIO, regardless of whether
        it started out as a BytesIO stream or a path to a file on disk."""
        if isinstance(self.file_path, BytesIO):
            self.file_path = self._bytesio_to_pdf(self.file_path)
            return self.file_path

        # str / Path input - was previously never converted, so docx/image
        # paths were handed to pymupdf as-is and would fail to open.
        self.file_path = self._file_to_pdf(self.file_path)
        return self.file_path

    def _detect_bytesio_type(self, buf: BytesIO) -> str:
        """Peek at header bytes of a BytesIO stream to guess its file type.
        Returns an extension like '.pdf', '.docx', '.png', or '' if unknown.
        Stream position is restored afterward.
        """
        pos = buf.tell()
        header = buf.read(8)
        buf.seek(pos)

        if header.startswith(b"%PDF-"):
            return ".pdf"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if header.startswith(b"\xff\xd8\xff"):
            return ".jpeg"
        if header.startswith(b"BM"):
            return ".bmp"
        if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
            return ".tiff"
        if header.startswith(b"PK\x03\x04"):
            import zipfile
            buf.seek(pos)
            try:
                with zipfile.ZipFile(buf) as zf:
                    names = zf.namelist()
                    if any(n.startswith("word/") for n in names):
                        result = ".docx"
                    elif any(n.startswith("xl/") for n in names):
                        result = ".xlsx"
                    elif any(n.startswith("ppt/") for n in names):
                        result = ".pptx"
                    else:
                        result = ".zip"
            except zipfile.BadZipFile:
                result = ""
            finally:
                buf.seek(pos)
            return result

        return ""

    def _bytesio_to_pdf(self, buf: BytesIO) -> BytesIO | None:
        """Converts a random BytesIO into a PDF BytesIO"""
        ext = self._detect_bytesio_type(buf)
        logger.info(f"[PDFLoader] Detected BytesIO content type: '{ext or 'unknown'}'")

        if ext == ".pdf":
            return buf

        elif ext == ".docx":
            logger.info("[PDFLoader] Converting in-memory DOCX to PDF")
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                temp_docx = temp_dir / "input.docx"

                temp_docx.write_bytes(buf.getvalue())
                self._convert_docx_libreoffice(temp_docx, temp_dir)

                actual_pdf_path = temp_dir / "input.pdf"
                returning_buf = BytesIO(actual_pdf_path.read_bytes())

            returning_buf.seek(0)
            return returning_buf

        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            logger.info("[PDFLoader] Using pillow for in-memory image conversion")
            try:
                buf.seek(0)
                img = Image.open(buf)
                pdf_bytes_io = self._convert_img_to_pdf(img)
                return pdf_bytes_io
            except Exception as e:
                logger.error(f"[PDFLoader] Error in image conversion: {e}")
                return None

        else:
            logger.error(f"[PDFLoader] Trying to convert '{ext or 'unknown'}' which isn't implemented")
            return None

    def _file_to_pdf(self, file_path: Path | str) -> BytesIO | None:
        """Converts a file to PDF BytesIO"""
        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()

        if ext == ".pdf":
            return BytesIO(path_obj.read_bytes())

        elif ext == ".docx":
            logger.info(f"[PDFLoader] Converting DOCX to PDF: '{file_path}'")
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)
                self._convert_docx_libreoffice(path_obj, temp_dir)

                actual_pdf_path = temp_dir / f"{path_obj.stem}.pdf"
                returning_buf = BytesIO(actual_pdf_path.read_bytes())

            returning_buf.seek(0)
            return returning_buf

        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            logger.info(f"[PDFLoader] Using pillow for image-security: '{file_path}'")

            try:
                img = Image.open(path_obj)
                pdf_bytes_io = self._convert_img_to_pdf(img)
                return pdf_bytes_io
            except Exception as e:
                logger.error(f"[PDFLoader] Error in image conversion: {e}")
                return None

        else:
            logger.error(f"[PDFLoader] Trying to convert '{ext or 'unknown'}' which isn't implemented")
            return None

    def _convert_img_to_pdf(self, img: ImageFile.ImageFile) -> BytesIO:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # convert to stream for pymupdf and make it into jpeg so the file is smaller
        clean_image_bytes = BytesIO()
        img.save(
            clean_image_bytes,
            format="JPEG",
            quality=self.image_quality,
            optimize=self.optimize_images
        )
        clean_image_bytes.seek(0)

        img_doc = pymupdf.open(stream=clean_image_bytes, filetype="jpeg")
        try:
            returning_buf = BytesIO(img_doc.convert_to_pdf())
        finally:
            img_doc.close()

        returning_buf.seek(0)
        return returning_buf

    def _convert_docx_libreoffice(self, input_path: Path, output_dir: Path):
        """Converting DOCX to PDF with LibreOffice without COM-Error."""
        import platform, subprocess

        if platform.system() == "Windows":
            libre_office_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        elif platform.system() == "Darwin":  # Mac
            libre_office_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        else:
            libre_office_path = "soffice"

        process = subprocess.run([
            libre_office_path,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(input_path)
        ], capture_output=True)

        if process.returncode != 0:
            raise RuntimeError(f"LibreOffice Error: {process.stderr.decode()}")