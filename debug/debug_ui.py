from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import sys
import ctypes

# Pfad zu den Modulen auflösen
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from py_impose import PDFProcessor, PaperTypes, PageSize
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
)


def set_high_dpi_awareness():
    """Aktiviert die High-DPI-Erkennung, damit die UI auf 4K-Monitoren scharf bleibt."""
    try:
        # Windows 10 / 11
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # Fallback für ältere Windows-Versionen
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class ImposeUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("py-impose Debug-Tool")

        # Verhindert, dass der Benutzer die Fenstergröße verändert
        self.root.resizable(False, False)

        # Ein modernes Standard-Theme erzwingen (z.B. 'vista' oder 'xpnative' unter Windows)
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        # Hauptcontainer mit großzügigem Innenabstand
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # =====================================================================
        # Sektion: Dateipfade
        # =====================================================================
        file_frame = ttk.LabelFrame(main_frame, text=" Dateipfade ", padding="10")
        file_frame.grid(row=0, column=0, columnspan=3, pady=(0, 15), sticky="ew")

        # Eingabedatei
        ttk.Label(file_frame, text="Eingabedatei:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.entry_input = ttk.Entry(file_frame, width=55)
        self.entry_input.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Durchsuchen", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)

        # Ausgabeordner
        ttk.Label(file_frame, text="Ausgabeordner:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_output = ttk.Entry(file_frame, width=55)
        self.entry_output.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(file_frame, text="Durchsuchen", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)

        # Dateiname
        ttk.Label(file_frame, text="Dateiname:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_filename = ttk.Entry(file_frame, width=55)
        self.entry_filename.insert(0, "output.pdf")
        self.entry_filename.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        # =====================================================================
        # Sektion: Einstellungen
        # =====================================================================
        config_frame = ttk.LabelFrame(main_frame, text=" Layout & Optionen ", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, pady=(0, 15), sticky="ew")

        # Kachel-Größe
        ttk.Label(config_frame, text="Kachel-Größe:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.combo_tile = ttk.Combobox(config_frame, values=[p.name for p in PaperTypes], state="readonly", width=15)
        self.combo_tile.set("SRA3")
        self.combo_tile.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Resizing
        ttk.Label(config_frame, text="Resizing (Optional):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.combo_resize = ttk.Combobox(config_frame, values=["Kein", *[p.name for p in PaperTypes]], state="readonly",
                                         width=15)
        self.combo_resize.set("Kein")
        self.combo_resize.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Anschnitt (mm)
        ttk.Label(config_frame, text="Anschnitt (mm):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_bleed = ttk.Entry(config_frame, width=10)
        self.entry_bleed.insert(0, "20.0")
        self.entry_bleed.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Liniendicke
        ttk.Label(config_frame, text="Liniendicke:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.entry_line_thick = ttk.Entry(config_frame, width=10)
        self.entry_line_thick.insert(0, "0.5")
        self.entry_line_thick.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        # Außenrand (mm)
        ttk.Label(config_frame, text="Außenrand (mm):").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.entry_margin = ttk.Entry(config_frame, width=10)
        self.entry_margin.insert(0, "1.0")
        self.entry_margin.grid(row=4, column=1, sticky="w", padx=5, pady=5)

        # Innenabstand (mm)
        ttk.Label(config_frame, text="Innenabstand (mm):").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        self.entry_inner = ttk.Entry(config_frame, width=10)
        self.entry_inner.insert(0, "0.0")
        self.entry_inner.grid(row=5, column=1, sticky="w", padx=5, pady=5)

        # Checkboxen
        self.scaleBleed = tk.BooleanVar(value=True)
        self.check_scale = ttk.Checkbutton(config_frame, text="Anschnitt skalieren", variable=self.scaleBleed)
        self.check_scale.grid(row=6, column=1, sticky="w", padx=5, pady=3)

        self.draw_lines = tk.BooleanVar(value=True)
        self.check_lines = ttk.Checkbutton(config_frame, text="Schnittlinien zeichnen", variable=self.draw_lines)
        self.check_lines.grid(row=7, column=1, sticky="w", padx=5, pady=3)

        # =====================================================================
        # Sektion: Start-Button
        # =====================================================================
        # Ein ttk-Button nutzt die OS-Stile, Farbänderungen per bg/fg klappen hier nur über Styles,
        # daher ist es als sauberer Standard-Aktionsbutton eingebunden.
        self.btn_start = ttk.Button(main_frame, text="PROZESS STARTEN", command=self.run_process)
        self.btn_start.grid(row=2, column=0, columnspan=3, pady=(10, 5), ipady=5, sticky="ew")

    def browse_input(self) -> None:
        file = filedialog.askopenfilename(filetypes=[("PDF Dateien", "*.pdf")])
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

            processor.update_value(
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