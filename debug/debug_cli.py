import sys
from pathlib import Path

src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

import logging
from py_impose import PDFProcessor, PaperTypes

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
)


def run_local_test():
    print("=== Starting py-impose Debug Test ===")

    current_dir = Path(__file__).resolve().parent

    input_file = current_dir / "Files" / "Inputs" / "test_input.jpg"
    output_file = current_dir / "Files" / "Outputs" / "output.pdf"

    if not input_file.exists():
        print(f"\n[ERROR] Please drop a test PDF file here: {input_file}")
        print("Then run this debug script again.\n")
        return

    processor = PDFProcessor(
        input_path=input_file,
        output_path=output_file,
        tile_to=PaperTypes.A0.value,
    )

    processor.update_value(
        load__image_quality=85,
        load__optimize_images=True,

        tile__inner_spacing=2,
        tile__line_thickness=2,
        tile__outer_margin=3.0,
        tile__draw_lines=True,

        bleed__default_bleed=10,
        bleed__scaleForBleed=False,
    )

    processor.run()

    print("=== Debug Test Finished! ===")
    if output_file.exists():
        print(f"Success! Check your output here: {output_file}")


if __name__ == "__main__":
    run_local_test()