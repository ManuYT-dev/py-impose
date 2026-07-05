# PDFProcessor – Reference Guide

The `PDFProcessor` is the core pipeline class of `py-impose`. It allows you to load, resize, impose, add bleed, tile, and export PDF documents in a clean, chainable workflow.

## Basic Initialization

To start a pipeline, instantiate the `PDFProcessor` with your input and output paths, and the target size you want to tile to.

```python
from py_impose import PDFProcessor, PaperTypes

processor = PDFProcessor(
    input_path="input.pdf",
    output_path="output_sra3.pdf",
    tile_to=PaperTypes.SRA3.value
)
```

## The Pipeline Workflow

The processor uses a chainable API. You can run individual steps or execute the entire pipeline at once using `.run()`.

```python
# Run everything automatically:
processor.run()

# OR run steps manually if you need custom logic in between:
processor.load().resize().impose().bleed().tile().export()
```

> **Note on ordering:** `impose()` always runs after `resize()` and before `bleed()`. Pages need to be the same size before they're reordered/merged into spreads, and bleed needs to be calculated on the final merged sheet — not on the individual sub-pages that make it up — or it ends up padding into the middle of a spread instead of the sheet's real outer edge.

---

## Dynamic Configuration (`update_value`)

The true power of the `PDFProcessor` comes from its `update_value(**kwargs)` method. This allows you to dynamically change settings for specific pipeline stages without re-initializing the class.

Use the `group__key` syntax to target specific pipeline modules. 

> **⚠️ Important Note on Units:** All layout measurements (margins, spacing, line thickness, bleed, panel shrink) are expected in **Points (pt)**, not millimeters! You can use `PageSize.mm_to_points(mm_value)` to convert them easily.

### 1. Global Attributes
Passed directly (e.g., `processor.update_value(farbe=True)`).

| Key | Type | Description |
| :--- | :--- | :--- |
| `bindung` | `BindingType \| str` | Binding type: `NORMAL` (default), `BOOK`, or `FLYER`. Only used as a fallback if `impose__binding` isn't set. |

### 2. Pipeline Stage Settings
Passed using the `group__key` syntax (e.g., `processor.update_value(tile__draw_lines=False)`).

| Group | Key | Type                 | Description                                                                                                                                                                         |
| :--- | :--- |:---------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **load** | `start` | `int`                | Page number to start loading from.                                                                                                                                                  |
| **load** | `end` | `int`                | Page number to stop loading at.                                                                                                                                                     |
| **load** | `steps` | `int`                | Step size for loading pages (e.g., every 2nd page).                                                                                                                                 |
| **load** | `image_quality` | `int`                | JPEG conversion quality (1-100) for image files. Defaults to 85.                                                                                                                    |
| **load** | `optimize_images` | `bool`               | Whether to perform lossless compression on images. Defaults to `True`.                                                                                                              |
| **resize**| `size` | `PageSize`           | Target size to scale the original pages to.                                                                                                                                         |
| **impose**| `binding` | `BindingType \| str` | `NORMAL` (no-op, default), `BOOK` (saddle-stitch), or `FLYER` (panel fold).                                                                                                         |
| **impose**| `pages_per_sheet` | `int`                | Panels per sheet. Only relevant for `FLYER` — `BOOK` always pads to a multiple of 4 internally, regardless of this value. Defaults to `2`.                                          |
| **impose**| `fold_style` | `str`                | `FLYER` only: `"accordion"` (equal panel widths) or `"letter"` (one panel shrunk so it tucks inside the others). Defaults to `"accordion"`.                                         |
| **impose**| `panel_shrink` | `float`              | `FLYER` + `"letter"` only: how much narrower the tucked-in panel is, in **pt**. Defaults to `PageSize.mm_to_points(2)`.                                                             |
| **impose**| `has_fold_margin` | `bool`               | `FLYER` + `"letter"` only: If the flyer already has a fold_margin build into the design or not. Defaults to `"False"`.                                                              |
| **bleed** | `default_bleed` | `float`              | Bleed area added to the page edges (in **pt**). Skipped automatically if a page already carries an explicit, designer-authored bleed box (including one inherited from imposition). |
| **bleed** | `scaleForBleed` | `bool`               | Whether to scale the content to fit the new bleed box.                                                                                                                              |
| **tile** | `output_size` | `PageSize`           | Target print sheet size (overrides `tile_to`).                                                                                                                                      |
| **tile** | `inner_spacing` | `float`              | Gap between individual tiled pages (in **pt**).                                                                                                                                     |
| **tile** | `outer_margin` | `float`              | Margin around the outside of the print sheet (in **pt**).                                                                                                                           |
| **tile** | `line_thickness` | `float`              | Thickness of the cutting/center lines (in **pt**).                                                                                                                                  |
| **tile** | `draw_lines` | `bool`               | Toggle cut marks on or off (`True`/`False`).                                                                                                                                        |
| **export**| `output_path` | `str/Path`           | Overrides the final output save location.                                                                                                                                           |

---

## Full Configuration Example

Here is an example of setting up a complex print job using dynamic values:

```python
from py_impose import PDFProcessor, PaperTypes, PageSize, BindingType

# Optional: Initialize logger if you want
import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
)

# 1. Initialize
processor = PDFProcessor("input.pdf", "output.pdf", tile_to=PaperTypes.SRA3.value)

# 2. Configure Settings
processor.update_value(
    # Global settings
    beidseitig=True,
    farbe=True,
    
    # Load configuration
    load__image_quality=85,
    load__optimize_images=True,

    # Imposition configuration (booklet example)
    impose__binding=BindingType.BOOK,

    # Bleed configuration
    bleed__default_bleed=PageSize.mm_to_points(3.0),
    bleed__scaleForBleed=False,
    
    # Tiling configuration
    tile__outer_margin=PageSize.mm_to_points(10.0),
    tile__inner_spacing=PageSize.mm_to_points(0.0),
    tile__line_thickness=0.5,
    tile__draw_lines=True
)

# 3. Execute
processor.run()
```

### Flyer example (tri-fold, letter fold)

```python
processor.update_value(
    impose__binding=BindingType.FLYER,
    impose__pages_per_sheet=3,
    impose__fold_style="letter",
    impose__panel_shrink=PageSize.mm_to_points(2.0),
)
processor.run()
```