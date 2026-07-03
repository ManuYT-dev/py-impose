import sys
from pathlib import Path
import time
from io import BytesIO

src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

import logging
from py_impose import PDFProcessor, PaperTypes

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
)

CURRENT_DIR = Path(__file__).resolve().parent
FILES_DIR = CURRENT_DIR / "Files"

results = {"passed": [], "failed": [], "skipped": []}


def _report(name: str, ok: bool | None, detail: str = ""):
    if ok is None:
        results["skipped"].append(name)
        print(f"[SKIP] {name} {detail}")
    elif ok:
        results["passed"].append(name)
        print(f"[PASS] {name} {detail}")
    else:
        results["failed"].append(name)
        print(f"[FAIL] {name} {detail}")


def _run_processor(name, input_path, output_file, **update_kwargs):
    """Shared helper: builds a processor, optionally applies update_value,
    runs the pipeline, and reports whether a non-empty output landed on disk."""
    try:
        processor = PDFProcessor(
            input_path=input_path,
            output_path=output_file,
            tile_to=PaperTypes.SRA3.value,
            resize_to=PaperTypes.A7.value,
        )
        if update_kwargs:
            processor.update_value(**update_kwargs)

        processor.run()

        ok = output_file.exists() and output_file.stat().st_size > 0
        _report(name, ok, f"- output at '{output_file}'")
    except Exception as e:
        _report(name, False, f"- raised {type(e).__name__}: {e}")


def test_load_from_file():
    """Does PDFProcessor work when input_path is a plain file path?"""
    name = "load from file path"
    input_file = FILES_DIR / "Inputs" / "test_input.pdf"
    output_file = FILES_DIR / "Outputs" / "output_from_file.pdf"

    if not input_file.exists():
        _report(name, None, f"- missing '{input_file}', drop a test PDF there and re-run")
        return

    _run_processor(name, input_file, output_file)


def test_load_from_buffer():
    """Does PDFProcessor work when input_path is an in-memory BytesIO buffer,
    instead of a path on disk? Assumes input_path accepts BytesIO the same
    way FileLoader does - adjust this test if that's not the case."""
    name = "load from BytesIO buffer"
    input_file = FILES_DIR / "Inputs" / "test_input.pdf"
    output_file = FILES_DIR / "Outputs" / "output_from_buffer.pdf"

    if not input_file.exists():
        _report(name, None, f"- missing '{input_file}'")
        return

    buf = BytesIO(input_file.read_bytes())
    _run_processor(name, buf, output_file)


def test_multiple_settings():
    """Does update_value() correctly apply several settings across
    different pipeline groups (tile__ and bleed__) at once?"""
    name = "multiple update_value settings (tile + bleed)"
    input_file = FILES_DIR / "Inputs" / "test_input.pdf"
    output_file = FILES_DIR / "Outputs" / "output_multi_settings.pdf"

    if not input_file.exists():
        _report(name, None, f"- missing '{input_file}'")
        return

    _run_processor(
        name,
        input_file,
        output_file,
        tile__inner_spacing=2,
        tile__line_thickness=2,
        tile__outer_margin=3.0,
        tile__draw_lines=True,
        bleed__default_bleed=10,
        bleed__scaleForBleed=False,
    )


def test_multiple_file_types():
    """Does the pipeline correctly accept and convert non-PDF input types
    (docx, png, jpg) alongside native PDFs? Optional fixtures are skipped
    individually if not present, rather than failing the whole run."""
    fixtures = {
        "test_input.pdf": "PDF",
        "test_input.docx": "DOCX",
        "test_input.png": "PNG",
        "test_input.jpg": "JPEG",
    }

    for filename, label in fixtures.items():
        name = f"file type support - {label}"
        input_file = FILES_DIR / "Inputs" / filename
        output_file = FILES_DIR / "Outputs" / f"output_filetype_{Path(filename).suffix}.pdf"

        if not input_file.exists():
            _report(name, None, f"- missing '{input_file}', drop a test {label} file there to include it")
            continue

        start_time = time.perf_counter()

        _run_processor(name, input_file, output_file)

        elapsed_time = time.perf_counter() - start_time
        print(f"    ⏱️ {label} conversion took {elapsed_time:.3f} seconds")

def main():
    print("=== py-impose Test Suite ===\n")
    FILES_DIR.mkdir(exist_ok=True)

    test_load_from_file()
    test_load_from_buffer()
    test_multiple_settings()
    test_multiple_file_types()

    total = len(results["passed"]) + len(results["failed"]) + len(results["skipped"])
    print("\n=== Summary ===")
    print(f"Total:   {total}")
    print(f"Passed:  {len(results['passed'])}")
    print(f"Failed:  {len(results['failed'])}")
    print(f"Skipped: {len(results['skipped'])}")

    if results["failed"]:
        print("\nFailed tests:")
        for name in results["failed"]:
            print(f"  - {name}")
        sys.exit(1)

    print("\n=== Test Suite Finished! ===")


if __name__ == "__main__":
    main()
