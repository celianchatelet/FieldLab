import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np

import fieldlab.geometries as geo
from fieldlab.solvers import solve
from fieldlab.app.panels.electrostatique import ElectrostatiquePanel
from fieldlab.app.panels.magneto import MagnetoPanel
from fieldlab.app.panels.thermique import ThermiquePanel
from .plot_panel import PlotPanel

# Registre : nom de domaine -> classe de panneau
_PANEL_CLS = {
    "Electrostatique":  ElectrostatiquePanel,
    "Magnetostatique":  MagnetoPanel,
    "Thermique":        ThermiquePanel,
}


class DomainPage(ttk.Frame):
    """
    Chaque page possede ses propres controles, son propre graphique, son
    propre resultat et sa propre boucle de calcul : les onglets n'interferent
    pas entre eux.
    """

    def __init__(self, master, domaine):
        super().__init__(master)
        self.domaine = domaine
        self.result = None
        self._queue = queue.Queue()

        panel_cls = _PANEL_CLS.get(domaine.nom, ElectrostatiquePanel)
        self.control = panel_cls(self, page=self)
        self.plot = PlotPanel(self, page=self)
        self.control.grid(row=0, column=0, sticky="ns")
        self.plot.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.after(100, self._poll)

    def run_simulation(self):
        try:
            p = self.control.read_params()
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("Parametres invalides", str(e)); return
        self.control.set_running(True)
        self.control.status.config(text="Calcul en cours...")
        self.control.progress.config(value=0)
        threading.Thread(target=self._worker, args=(p,), daemon=True).start()

    def _worker(self, p):
        try:
            q = p.get("q")   # puissance volumique (thermique) ou None
            field = geo.build(self.domaine.scenarios, p["geom"], p["N"], p["v"],
                              p["walls"], p["obstacles"], q=q)

            def prog(it, err):
                self._queue.put(("progress", min(100, 100 * it / p["max_iter"])))

            res = solve(field, p["method"], omega=p["omega"], tol=p["tol"],
                        max_iter=p["max_iter"], progress=prog)
            self._queue.put(("done", (res, p["viz"])))
        except Exception as e:
            self._queue.put(("error", str(e)))

    def _poll(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "progress":
                    self.control.progress.config(value=payload)
                elif kind == "done":
                    res, vizkind = payload
                    self.result = res
                    self.control.progress.config(value=100)
                    msg = (f"Converge en {res.iterations} iter. "
                           f"({res.temps:.2f} s, err={res.erreur:.1e})"
                           if res.converge else
                           f"NON converge ({res.iterations} iter.)")
                    self.control.status.config(text=msg)
                    self.control.set_running(False)
                    self.plot.redraw(vizkind)
                elif kind == "error":
                    messagebox.showerror("Erreur de simulation", payload)
                    self.control.status.config(text="Erreur.")
                    self.control.set_running(False)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def reinitialiser(self):
        self.control._vider_obstacles()
        self.result = None
        self.control.progress.config(value=0)
        self.control.status.config(text="Pret.")
        self.plot.reset()

    def export_png(self):
        if self.result is None:
            messagebox.showinfo("Rien a exporter", "Lancez d'abord une simulation."); return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png")])
        if path:
            self.plot.save_png(path)
            self.control.status.config(text=f"Figure exportee : {path}")

    def export_csv(self):
        if self.result is None:
            messagebox.showinfo("Rien a exporter", "Lancez d'abord une simulation."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            np.savetxt(path, self.result.champ.V, delimiter=",")
            self.control.status.config(text=f"Champ exporte : {path}")
