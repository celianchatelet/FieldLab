import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure

from fieldlab import viz


class PlotPanel(ttk.Frame):
    """Graphique d'UNE page. Lit l'etat et le domaine via page."""

    def __init__(self, master, page):
        super().__init__(master, padding=4)
        self.page = page
        self.figure = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        barre = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        barre.update()
        barre.pack(side="bottom", fill="x")
        self._accueil()

    def redraw(self, kind):
        res = self.page.result
        if res is None:
            return
        dom = self.page.domaine
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        viz.dessiner(self.ax, res.champ, kind,
                     dom.champ_fn, dom.scalaire, dom.champ)
        self.figure.tight_layout()
        self.canvas.draw()

    def save_png(self, path):
        self.figure.savefig(path, dpi=200, bbox_inches="tight")

    def reset(self):
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        self._accueil()

    def _accueil(self):
        self.ax.text(0.5, 0.5,
                     f"{self.page.domaine.nom}\nConfigurez puis lancez la simulation",
                     ha="center", va="center", fontsize=13, color="gray")
        self.ax.set_axis_off()
        self.canvas.draw()
