import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import sys

src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from py_impose import PDFProcessor, PaperTypes, PageSize


class ImposeUI:
    def __init__(self, root):
        self.root = root
        self.root.title("py-impose Debug-Tool")

        tk.Label(root, text="Eingabedatei:").grid(row=0, column=0, sticky="e")
        self.entry_input = tk.Entry(root, width=50)
        self.entry_input.grid(row=0, column=1)
        tk.Button(root, text="Durchsuchen", command=self.browse_input).grid(row=0, column=2)

        tk.Label(root, text="Ausgabeordner:").grid(row=1, column=0, sticky="e")
        self.entry_output = tk.Entry(root, width=50)
        self.entry_output.grid(row=1, column=1)
        tk.Button(root, text="Durchsuchen", command=self.browse_output).grid(row=1, column=2)

        tk.Label(root, text="Dateiname:").grid(row=2, column=0, sticky="e")
        self.entry_filename = tk.Entry(root, width=50)
        self.entry_filename.insert(0, "output.pdf")
        self.entry_filename.grid(row=2, column=1)

        tk.Label(root, text="Kachel-Größe:").grid(row=3, column=0, sticky="e")
        self.combo_tile = ttk.Combobox(root, values=[p.name for p in PaperTypes], state="readonly")
        self.combo_tile.set("SRA3")
        self.combo_tile.grid(row=3, column=1, sticky="w")

        tk.Label(root, text="Resizing (Optional):").grid(row=4, column=0, sticky="e")
        self.combo_resize = ttk.Combobox(root, values=["Kein", *[p.name for p in PaperTypes]], state="readonly")
        self.combo_resize.set("Kein")
        self.combo_resize.grid(row=4, column=1, sticky="w")

        tk.Label(root, text="Anschnitt (mm):").grid(row=5, column=0, sticky="e")
        self.entry_bleed = tk.Entry(root, width=10)
        self.entry_bleed.insert(0, "5.0")
        self.entry_bleed.grid(row=5, column=1, sticky="w")

        self.draw_lines = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="Schnittlinien zeichnen", variable=self.draw_lines).grid(row=6, column=1, sticky="w")

        tk.Label(root, text="Liniendicke:").grid(row=7, column=0, sticky="e")
        self.entry_line_thick = tk.Entry(root, width=10)
        self.entry_line_thick.insert(0, "0.5")
        self.entry_line_thick.grid(row=7, column=1, sticky="w")

        tk.Label(root, text="Außenrand (mm):").grid(row=8, column=0, sticky="e")
        self.entry_margin = tk.Entry(root, width=10)
        self.entry_margin.insert(0, "10.0")
        self.entry_margin.grid(row=8, column=1, sticky="w")

        tk.Label(root, text="Innenabstand (mm):").grid(row=9, column=0, sticky="e")
        self.entry_inner = tk.Entry(root, width=10)
        self.entry_inner.insert(0, "0.0")
        self.entry_inner.grid(row=9, column=1, sticky="w")

        tk.Button(root, text="PROZESS STARTEN", command=self.run_process, bg="green", fg="white").grid(row=10, column=1,
                                                                                                       pady=20)

    def browse_input(self):
        file = filedialog.askopenfilename(filetypes=[("PDF Dateien", "*.pdf")])
        if file:
            self.entry_input.delete(0, tk.END)
            self.entry_input.insert(0, file)

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, folder)

    def run_process(self):
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

            processor.update_value(
                tile__line_thickness=float(self.entry_line_thick.get()),
                tile__outer_margin_mm=float(self.entry_margin.get()),
                tile__inner_spacing_mm=float(self.entry_inner.get()),
                tile__draw_lines=self.draw_lines.get(),
                bleed__default_bleed_pt=bleed_pt
            )

            processor.run()
            messagebox.showinfo("Erfolg", f"Datei gespeichert unter:\n{out_path}")

        except ValueError as ve:
            messagebox.showerror("Eingabefehler", f"Bitte Zahlenwerte prüfen: {ve}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImposeUI(root)
    root.mainloop()