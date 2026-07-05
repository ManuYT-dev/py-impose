from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import sys
import ctypes

src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

import logging
from py_impose import PDFProcessor, PaperTypes, PageSize, BindingType

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
)


def set_high_dpi_awareness():
    """Activate the High-DPI-Recognizer, so that UI stays sharp on 4K-Monitors."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class ImposeUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("py-impose Debug-Tool")

        self.root.resizable(False, False)

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.file_frame = ttk.LabelFrame(main_frame, text=" Dateipfade ", padding="10")
        self.file_frame.grid(row=0, column=0, columnspan=3, pady=(0, 15), sticky="ew")

        ttk.Label(self.file_frame, text="Eingabedatei:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.entry_input = ttk.Entry(self.file_frame, width=55)
        self.entry_input.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.file_frame, text="Durchsuchen", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(self.file_frame, text="Ausgabeordner:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_output = ttk.Entry(self.file_frame, width=55)
        self.entry_output.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.file_frame, text="Durchsuchen", command=self.browse_output).grid(row=1, column=2, padx=5,
                                                                                         pady=5)

        ttk.Label(self.file_frame, text="Dateiname:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_filename = ttk.Entry(self.file_frame, width=55)
        self.entry_filename.insert(0, "output.pdf")
        self.entry_filename.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        self.config_frame = ttk.LabelFrame(main_frame, text=" Layout & Optionen ", padding="10")
        self.config_frame.grid(row=1, column=0, columnspan=3, pady=(0, 15), sticky="ew")

        ttk.Label(self.config_frame, text="Kachel-Größe:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.combo_tile = ttk.Combobox(self.config_frame, values=[p.name for p in PaperTypes], state="readonly",
                                       width=15)
        self.combo_tile.set("SRA3")
        self.combo_tile.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(self.config_frame, text="Resizing (Optional):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.combo_resize = ttk.Combobox(self.config_frame, values=["Kein", *[p.name for p in PaperTypes]],
                                         state="readonly", width=15)
        self.combo_resize.set("Kein")
        self.combo_resize.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(self.config_frame, text="Anschnitt (mm):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_bleed = ttk.Entry(self.config_frame, width=10)
        self.entry_bleed.insert(0, "20.0")
        self.entry_bleed.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(self.config_frame, text="Liniendicke (mm):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.entry_line_thick = ttk.Entry(self.config_frame, width=10)
        self.entry_line_thick.insert(0, "0.5")
        self.entry_line_thick.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(self.config_frame, text="Außenrand (mm):").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.entry_margin = ttk.Entry(self.config_frame, width=10)
        self.entry_margin.insert(0, "1.0")
        self.entry_margin.grid(row=4, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(self.config_frame, text="Innenabstand (mm):").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        self.entry_inner = ttk.Entry(self.config_frame, width=10)
        self.entry_inner.insert(0, "0.0")
        self.entry_inner.grid(row=5, column=1, sticky="w", padx=5, pady=5)

        self.scaleBleed = tk.BooleanVar(value=True)
        self.check_scale = ttk.Checkbutton(self.config_frame, text="Anschnitt skalieren", variable=self.scaleBleed)
        self.check_scale.grid(row=6, column=1, sticky="w", padx=5, pady=3)

        self.draw_lines = tk.BooleanVar(value=True)
        self.check_lines = ttk.Checkbutton(self.config_frame, text="Schnittlinien zeichnen", variable=self.draw_lines)
        self.check_lines.grid(row=7, column=1, sticky="w", padx=5, pady=3)

        # --- Optional Binding / Impose Settings Frame ---
        self.impose_frame = ttk.LabelFrame(main_frame, text=" Bindung (Optional, für Bücher/Flyer) ", padding="10")
        self.impose_frame.grid(row=2, column=0, columnspan=3, pady=(0, 15), sticky="ew")

        ttk.Label(self.impose_frame, text="Bindungstyp:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.combo_binding = ttk.Combobox(self.impose_frame, values=[b.name for b in BindingType],
                                          state="readonly", width=15)
        self.combo_binding.set(BindingType.NORMAL.name)
        self.combo_binding.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.combo_binding.bind("<<ComboboxSelected>>", self._on_binding_change)

        ttk.Label(self.impose_frame, text="Seiten pro Bogen:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_pages_per_sheet = ttk.Entry(self.impose_frame, width=10)
        self.entry_pages_per_sheet.insert(0, "2")
        self.entry_pages_per_sheet.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.label_fold_style = ttk.Label(self.impose_frame, text="Faltart (nur Flyer):")
        self.label_fold_style.grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.combo_fold_style = ttk.Combobox(self.impose_frame, values=["accordion", "letter"],
                                             state="readonly", width=15)
        self.combo_fold_style.set("accordion")
        self.combo_fold_style.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.label_panel_shrink = ttk.Label(self.impose_frame, text="Panel-Verkleinerung (mm):")
        self.label_panel_shrink.grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.entry_panel_shrink = ttk.Entry(self.impose_frame, width=10)
        self.entry_panel_shrink.insert(0, "2.0")
        self.entry_panel_shrink.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        self._on_binding_change()  # set initial enabled/disabled state

        # --- Optional Image Settings Frame ---
        self.image_settings_frame = ttk.LabelFrame(main_frame, text=" Bildeinstellungen (Optional, nur für Bilder) ",
                                                   padding="10")
        self.image_settings_frame.grid(row=3, column=0, columnspan=3, pady=(0, 15), sticky="ew")

        self.image_quality_var = tk.IntVar(value=85)
        self.optimize_images_var = tk.BooleanVar(value=True)

        self.quality_label = ttk.Label(self.image_settings_frame, text="JPEG Qualität (1-100):")
        self.quality_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)

        self.quality_scale = ttk.Scale(
            self.image_settings_frame,
            from_=1,
            to=100,
            orient="horizontal",
            variable=self.image_quality_var,
            command=lambda val: self.image_quality_var.set(int(float(val)))  # Forces integer updates
        )
        self.quality_scale.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.quality_value_label = ttk.Label(self.image_settings_frame, textvariable=self.image_quality_var, width=3)
        self.quality_value_label.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        # Optimize Control
        self.optimize_check = ttk.Checkbutton(
            self.image_settings_frame,
            text="Verlustfreie Optimierung (Lossless)",
            variable=self.optimize_images_var
        )
        self.optimize_check.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=3)

        self.btn_start = ttk.Button(main_frame, text="PROZESS STARTEN", command=self.run_process)
        self.btn_start.grid(row=4, column=0, columnspan=3, pady=(10, 5), ipady=5, sticky="ew")

    def _on_binding_change(self, _event=None) -> None:
        """Fold style / panel shrink only make sense for FLYER binding — grey them out otherwise."""
        is_flyer = self.combo_binding.get() == BindingType.FLYER.name
        state = "readonly" if is_flyer else "disabled"
        entry_state = "normal" if is_flyer else "disabled"
        self.combo_fold_style.configure(state=state)
        self.entry_panel_shrink.configure(state=entry_state)

    def browse_input(self) -> None:
        file = filedialog.askopenfilename(filetypes=[
            ("Alle unterstützten Dateien", "*.pdf *.docx *.png *.jpg *.jpeg *.bmp *.tiff"),
            ("PDF Dateien", "*.pdf"),
            ("Word Dokumente", "*.docx"),
            ("Bilddateien", "*.png *.jpg *.jpeg *.bmp *.tiff"),
            ("Alle Dateien", "*.*"),
        ])
        if file:
            self.entry_input.delete(0, tk.END)
            self.entry_input.insert(0, file)

    def browse_output(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, folder)

    def run_process(self) -> None:
        try:
            out_path = Path(self.entry_output.get()) / self.entry_filename.get()

            tile_name = self.combo_tile.get()
            resize_name = self.combo_resize.get()

            tile_size = PaperTypes[tile_name].value
            resize_size = PaperTypes[resize_name].value if resize_name != "Kein" else None

            processor = PDFProcessor(
                input_path=self.entry_input.get(),
                output_path=str(out_path),
                tile_to=tile_size,
                resize_to=resize_size
            )

            bleed_pt = PageSize.mm_to_points(float(self.entry_bleed.get()))
            line_thickness_pt = PageSize.mm_to_points(float(self.entry_line_thick.get()))
            inner_spacing_pt = PageSize.mm_to_points(float(self.entry_inner.get()))
            outer_margin_pt = PageSize.mm_to_points(float(self.entry_margin.get()))

            binding = BindingType[self.combo_binding.get()]
            pages_per_sheet = int(self.entry_pages_per_sheet.get())
            fold_style = self.combo_fold_style.get()
            panel_shrink_pt = PageSize.mm_to_points(float(self.entry_panel_shrink.get()))

            processor.update_value(
                load__image_quality=self.image_quality_var.get(),
                load__optimize_images=self.optimize_images_var.get(),
                impose__binding=binding,
                impose__pages_per_sheet=pages_per_sheet,
                impose__fold_style=fold_style,
                impose__panel_shrink=panel_shrink_pt,
                tile__line_thickness=line_thickness_pt,
                tile__outer_margin=outer_margin_pt,
                tile__inner_spacing=inner_spacing_pt,
                tile__draw_lines=self.draw_lines.get(),
                bleed__default_bleed=bleed_pt,
                bleed__scaleForBleed=self.scaleBleed.get(),
            )

            processor.run()
            messagebox.showinfo("Erfolg", f"Datei gespeichert unter:\n{out_path}")

        except ValueError as ve:
            messagebox.showerror("Eingabefehler", f"Bitte Zahlenwerte prüfen: {ve}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    set_high_dpi_awareness()
    root = tk.Tk()
    app = ImposeUI(root)
    root.mainloop()