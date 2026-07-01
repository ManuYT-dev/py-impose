# py-impose 🖨️

A professional Python library for PDF imposition, resizing, and tiling. Easily prepare PDF documents for print using a clean, pipeline-oriented API.

## Motivation
I originally built `py-impose` to handle automated imposition for web-to-print order systems, specifically dealing with dynamic A4 to SRA3 conversions and stapling logic. I realized this pipeline could be highly useful to other developers dealing with print automation, so I extracted it into this standalone, open-source library. Whether you are building a full print-shop backend or just need to tile some PDFs for a personal project, I hope this helps!

## Key Features
- **Pipeline Processing:** Load, resize, bleed, tile, and export PDFs in a single chain.
- **Intelligent Tiling:** Automatically computes grids for optimal printing on target paper sizes (e.g., A4 onto SRA3).
- **Dynamic Configuration:** Use a unified `update_value()` method to tweak cut lines, margins, and bleed on the fly.
- **Native PDF Units:** Built entirely around standard PDF points (pt) for absolute precision, with built-in helpers for millimeter conversion.

## Installation

You can install `py-impose` directly with [PIP](https://pypi.org/project/py-impose/):
```bash
pip install py-impose
```

or build it from source:
```bash
git clone [https://github.com/ManuYT-dev/py-impose.git](https://github.com/ManuYT-dev/py-impose.git)
cd py-impose
pip install -e .
```

*Note: This library requires `pymupdf` to handle the heavy lifting of PDF manipulation.*

## Quick Start

The core of the library is the `PDFProcessor` class, which allows you to chain commands together.

```python
from py_impose import PDFProcessor, PaperTypes, PageSize

# Initialize the pipeline
processor = PDFProcessor(
    input_path="input_design.pdf",
    output_path="print_ready_SRA3.pdf",
    tile_to=PaperTypes.SRA3.value
)

# Configure layout settings (Values are in points)
processor.update_value(
    tile__outer_margin=PageSize.mm_to_points(10.0),
    tile__line_thickness=0.5,
    tile__draw_lines=True,
    bleed__default_bleed=PageSize.mm_to_points(3.0)
)

# Run the full process
processor.run()
```

## Documentation

For a complete list of all configurable parameters, dynamic settings, and advanced usage, please read the **[PDFProcessor Reference Guide](docs/PDFProcessor.md)**.

## Debugging UI

The repository includes a built-in `tkinter` graphical interface for testing and debugging your PDF layouts locally.
To use it, run:
```bash
python debug/debug_ui.py
```

## Contributing

Contributions are always welcome! If you find a bug or have an idea for a new feature (like new binding logic or paper formats), feel free to open an issue or submit a pull request.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0. 
You are free to use, modify, and distribute this software for personal or educational purposes, but commercial use is strictly prohibited. See the [LICENSE](LICENSE) file for full details.
