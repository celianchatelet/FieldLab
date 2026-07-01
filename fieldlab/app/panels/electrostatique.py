"""Panneau de controle du domaine electrostatique.

Parametres : Tension V (electrodes).
Obstacles  : conducteur (Dirichlet a une tension V) / isolant (trou).
Parois     : neumann (bord libre) ou dirichlet (tension imposee V).
"""
import tkinter as tk
from tkinter import ttk

from fieldlab.obstacles import FORMES
from fieldlab.app.panels.base import BasePanel, COTES

# Labels des parametres de paroi selon le type
_PARAM_LABELS = {
    "neumann":   ("", ""),
    "dirichlet": ("V", ""),
}


class ElectrostatiquePanel(BasePanel):

    def __init__(self, master, page):
        # Initialiser les attributs AVANT super().__init__ car _build() les utilise
        self.obstacles = []
        self.wall_kind = {c: tk.StringVar(value="neumann") for c in COTES}
        self.wall_p1   = {c: tk.DoubleVar(value=0.0)       for c in COTES}
        self.wall_labA = {c: tk.StringVar(value="")         for c in COTES}
        self._wall_entA = {}
        self.var_v   = None   # cree dans _build_domain_params
        self.ob_forme = tk.StringVar(value="disque")
        self.ob_x     = tk.DoubleVar(value=0.5)
        self.ob_y     = tk.DoubleVar(value=0.5)
        self.ob_r     = tk.DoubleVar(value=0.1)
        self.ob_type  = tk.StringVar(value="isolant")
        self.ob_v     = tk.DoubleVar(value=5.0)
        super().__init__(master, page)

    # ------------------------------------------------------------------ build
    def _build_domain_params(self, host, dom):
        p = ttk.LabelFrame(host, text="Parametres", padding=6)
        p.pack(fill="x", pady=3)
        self.var_v = tk.DoubleVar(value=dom.defaut)
        r = ttk.Frame(p); r.pack(fill="x", pady=1)
        ttk.Label(r, text="Tension (V)").pack(side="left")
        ttk.Entry(r, textvariable=self.var_v, width=8).pack(side="right")
        self._row(p, "Resolution N", self.var_N)

    def _build_sources_obstacles(self, host, dom):
        o = ttk.LabelFrame(host, text="Obstacles", padding=6)
        o.pack(fill="x", pady=3)
        ttk.Label(o, foreground="gray", justify="left", wraplength=300,
                  text="conducteur : Dirichlet a une tension V\n"
                       "isolant    : trou (solid_mask)").pack(anchor="w", pady=(0, 4))
        r1 = ttk.Frame(o); r1.pack(fill="x")
        ttk.Combobox(r1, textvariable=self.ob_forme, values=list(FORMES),
                     state="readonly", width=10).pack(side="left")
        ttk.Combobox(r1, textvariable=self.ob_type,
                     values=["isolant", "conducteur"],
                     state="readonly", width=10).pack(side="left", padx=3)
        r2 = ttk.Frame(o); r2.pack(fill="x", pady=2)
        for lab, var in (("x", self.ob_x), ("y", self.ob_y),
                         ("taille", self.ob_r), ("V", self.ob_v)):
            ttk.Label(r2, text=lab).pack(side="left")
            ttk.Entry(r2, textvariable=var, width=5).pack(side="left", padx=2)
        r3 = ttk.Frame(o); r3.pack(fill="x")
        ttk.Button(r3, text="Ajouter", command=self._ajouter).pack(side="left")
        ttk.Button(r3, text="Vider", command=self._vider_obstacles).pack(side="left", padx=3)
        self.liste = tk.Listbox(o, height=4)
        self.liste.pack(fill="x", pady=(3, 0))

    def _build_walls(self, host, dom):
        w = ttk.LabelFrame(host, text="Parois du domaine", padding=6)
        w.pack(fill="x", pady=3)
        ttk.Label(w, foreground="gray", justify="left", wraplength=300,
                  text="neumann : bord libre  ·  dirichlet : tension imposee (V)").pack(
            anchor="w", pady=(0, 4))
        grid = ttk.Frame(w); grid.pack(fill="x")
        for col, txt in ((0, "Cote"), (1, "Condition"), (2, "V")):
            ttk.Label(grid, text=txt, font=("", 8, "bold")).grid(
                row=0, column=col, sticky="w", padx=(0, 4), pady=(0, 2))
        for i, c in enumerate(COTES, start=1):
            ttk.Label(grid, text=c.capitalize()).grid(row=i, column=0, sticky="w", padx=(0, 4))
            cb = ttk.Combobox(grid, textvariable=self.wall_kind[c],
                              values=["neumann", "dirichlet"],
                              state="readonly", width=9)
            cb.grid(row=i, column=1, padx=(0, 8), pady=1)
            cb.bind("<<ComboboxSelected>>", lambda e, k=c: self._maj_paroi(k))
            ttk.Label(grid, textvariable=self.wall_labA[c], width=4,
                      foreground="#555").grid(row=i, column=2, sticky="e")
            eA = ttk.Entry(grid, textvariable=self.wall_p1[c], width=5)
            eA.grid(row=i, column=3, padx=(1, 8))
            self._wall_entA[c] = eA
        for c in COTES:
            self._maj_paroi(c)

    # ----------------------------------------------------------- parois
    def _maj_paroi(self, c):
        kind = self.wall_kind[c].get()
        la = "V" if kind == "dirichlet" else ""
        self.wall_labA[c].set(la)
        self._wall_entA[c].configure(state=("normal" if la else "disabled"))

    def _charger_parois(self, event=None):
        dom = self.page.domaine
        try:
            val = float(self.var_v.get()) if self.var_v else dom.defaut
        except (ValueError, tk.TclError):
            val = dom.defaut
        walls = dom.walls_defaut(self.var_geom.get(), val)
        for c in COTES:
            spec = walls.get(c, ("neumann",))
            self.wall_kind[c].set(spec[0])
            self.wall_p1[c].set(round(spec[1], 4) if spec[0] == "dirichlet" else 0.0)
            self._maj_paroi(c)

    # ----------------------------------------------------------- obstacles
    def _ajouter(self):
        forme = self.ob_forme.get()
        x, y, r = self.ob_x.get(), self.ob_y.get(), self.ob_r.get()
        bc = ("isolant",) if self.ob_type.get() == "isolant" else ("dirichlet", self.ob_v.get())
        if forme == "disque":
            args = {"cx": x, "cy": y, "r": r}
        elif forme == "rectangle":
            args = {"x0": x - r, "y0": y - r, "x1": x + r, "y1": y + r}
        elif forme == "anneau":
            args = {"cx": x, "cy": y, "r_ext": r, "r_int": 0.6 * r}
        elif forme == "segment_v":
            args = {"x": x, "y0": y - r, "y1": y + r}
        else:
            args = {"y": y, "x0": x - r, "x1": x + r}
        self.obstacles.append({"forme": forme, "args": args, "bc": bc})
        self.liste.insert("end", f"{forme} {self.ob_type.get()} ({x:.2f},{y:.2f}) t={r:.2f}")

    def _vider_obstacles(self):
        self.obstacles.clear()
        if hasattr(self, "liste"):
            self.liste.delete(0, "end")

    # ----------------------------------------------------------- params
    def _walls(self):
        d = {}
        for c in COTES:
            k = self.wall_kind[c].get()
            d[c] = ("dirichlet", float(self.wall_p1[c].get())) if k == "dirichlet" else ("neumann",)
        return d

    def contribute_params(self, d):
        d["v"]         = float(self.var_v.get())
        d["walls"]     = self._walls()
        d["obstacles"] = list(self.obstacles)
