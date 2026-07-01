import tkinter as tk
from tkinter import ttk

from fieldlab.domaines import DOMAINES
from .page import DomainPage


class FieldLabApp(tk.Tk):
    """Fenetre principale : un onglet (une page autonome) par domaine."""

    def __init__(self):
        super().__init__()
        self.title("FieldLab — Simulateur de champs 2D")
        self.geometry("1180x760")
        self.minsize(960, 620)

        self._build_menu()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.pages = {}
        for nom, dom in DOMAINES.items():
            page = DomainPage(self.notebook, dom)
            self.notebook.add(page, text=nom)
            self.pages[nom] = page

    def _page_active(self):
        return self.nametowidget(self.notebook.select())

    def _build_menu(self):
        bar = tk.Menu(self)
        m = tk.Menu(bar, tearoff=0)
        m.add_command(label="Exporter la figure (PNG)...",
                      command=lambda: self._page_active().export_png())
        m.add_command(label="Exporter le champ scalaire (CSV)...",
                      command=lambda: self._page_active().export_csv())
        m.add_separator()
        m.add_command(label="Quitter", command=self.destroy)
        bar.add_cascade(label="Fichier", menu=m)
        h = tk.Menu(bar, tearoff=0)
        h.add_command(label="A propos", command=self._about)
        bar.add_cascade(label="Aide", menu=h)
        self.config(menu=bar)

    def _about(self):
        from tkinter import messagebox
        messagebox.showinfo("A propos",
            "FieldLab\nSimulateur de champs 2D\n"
            "Laplace / Poisson — Jacobi / Gauss-Seidel / SOR\n"
            "Domaines : electrostatique, magnetostatique, thermique\n"
            "Une page (onglet) par domaine.")
