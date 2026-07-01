"""Panneau de controle du domaine thermique.

Modele : uniquement des temperatures imposees (Dirichlet) et des parois
adiabatiques (Neumann). Principe du maximum garanti : T reste toujours dans
l'intervalle [T_min_impose, T_max_impose].

Objets plaçables : un bloc a temperature imposee T (°C), forme disque ou
rectangle. Un seul champ numerique : T.

Conditions aux bords par cote : temperature imposee (T) ou isolee (adiabatique).
"""
import tkinter as tk
from tkinter import ttk

from fieldlab.app.panels.base import BasePanel, COTES

_WALL_TYPES = ["neumann", "dirichlet"]

_FORMES_OB = ["disque", "rectangle"]


class ThermiquePanel(BasePanel):

    def __init__(self, master, page):
        self.obstacles_th = []
        self.wall_kind = {c: tk.StringVar(value="neumann") for c in COTES}
        self.wall_p1   = {c: tk.DoubleVar(value=0.0)       for c in COTES}
        self.wall_labA = {c: tk.StringVar(value="")         for c in COTES}
        self._wall_entA = {}
        self.var_T_chaud = None   # cree dans _build_domain_params
        self.ob_forme = tk.StringVar(value="disque")
        self.ob_x     = tk.DoubleVar(value=0.5)
        self.ob_y     = tk.DoubleVar(value=0.5)
        self.ob_r     = tk.DoubleVar(value=0.1)
        self.ob_T     = tk.DoubleVar(value=50.0)
        super().__init__(master, page)

    # ------------------------------------------------------------------ build
    def _build_domain_params(self, host, dom):
        p = ttk.LabelFrame(host, text="Parametres", padding=6)
        p.pack(fill="x", pady=3)
        self.var_T_chaud = tk.DoubleVar(value=dom.defaut)
        r1 = ttk.Frame(p); r1.pack(fill="x", pady=1)
        ttk.Label(r1, text="T chaud (°C)").pack(side="left")
        ttk.Entry(r1, textvariable=self.var_T_chaud, width=8).pack(side="right")
        self._row(p, "Resolution N", self.var_N)

    def _build_sources_obstacles(self, host, dom):
        o = ttk.LabelFrame(host, text="Objets a temperature imposee", padding=6)
        o.pack(fill="x", pady=3)
        ttk.Label(o, foreground="gray", justify="left", wraplength=300,
                  text="Pose un objet a temperature uniforme et constante T (°C).\n"
                       "La solution reste bornee entre les temperatures imposees.").pack(
            anchor="w", pady=(0, 4))
        r1 = ttk.Frame(o); r1.pack(fill="x")
        ttk.Combobox(r1, textvariable=self.ob_forme, values=_FORMES_OB,
                     state="readonly", width=10).pack(side="left")
        r2 = ttk.Frame(o); r2.pack(fill="x", pady=2)
        for lab, var in (("x", self.ob_x), ("y", self.ob_y),
                         ("taille", self.ob_r), ("T (°C)", self.ob_T)):
            ttk.Label(r2, text=lab).pack(side="left")
            ttk.Entry(r2, textvariable=var, width=5).pack(side="left", padx=2)
        r3 = ttk.Frame(o); r3.pack(fill="x")
        ttk.Button(r3, text="Ajouter", command=self._ajouter_obstacle).pack(side="left")
        ttk.Button(r3, text="Vider", command=self._vider_obstacles).pack(side="left", padx=3)
        self.liste = tk.Listbox(o, height=4)
        self.liste.pack(fill="x", pady=(3, 0))

    def _build_walls(self, host, dom):
        w = ttk.LabelFrame(host, text="Parois du domaine", padding=6)
        w.pack(fill="x", pady=3)
        ttk.Label(w, foreground="gray", justify="left", wraplength=300,
                  text="neumann : paroi isolee (adiabatique)  ·  "
                       "dirichlet : temperature imposee T (°C)").pack(
            anchor="w", pady=(0, 4))
        grid = ttk.Frame(w); grid.pack(fill="x")
        for col, txt in ((0, "Cote"), (1, "Condition"), (2, "T (°C)")):
            ttk.Label(grid, text=txt, font=("", 8, "bold")).grid(
                row=0, column=col, sticky="w", padx=(0, 4), pady=(0, 2))
        for i, c in enumerate(COTES, start=1):
            ttk.Label(grid, text=c.capitalize()).grid(row=i, column=0, sticky="w", padx=(0, 4))
            cb = ttk.Combobox(grid, textvariable=self.wall_kind[c],
                              values=_WALL_TYPES, state="readonly", width=9)
            cb.grid(row=i, column=1, padx=(0, 8), pady=1)
            cb.bind("<<ComboboxSelected>>", lambda e, k=c: self._maj_paroi(k))
            ttk.Label(grid, textvariable=self.wall_labA[c], width=6,
                      foreground="#555").grid(row=i, column=2, sticky="e")
            eA = ttk.Entry(grid, textvariable=self.wall_p1[c], width=6)
            eA.grid(row=i, column=3, padx=(1, 4))
            self._wall_entA[c] = eA
        for c in COTES:
            self._maj_paroi(c)

    # ----------------------------------------------------------- parois
    def _maj_paroi(self, c):
        kind = self.wall_kind[c].get()
        la = "T (°C)" if kind == "dirichlet" else ""
        self.wall_labA[c].set(la)
        self._wall_entA[c].configure(state=("normal" if la else "disabled"))

    def _charger_parois(self, event=None):
        dom = self.page.domaine
        try:
            val = float(self.var_T_chaud.get()) if self.var_T_chaud else dom.defaut
        except (ValueError, tk.TclError):
            val = dom.defaut
        walls = dom.walls_defaut(self.var_geom.get(), val)
        for c in COTES:
            spec = walls.get(c, ("neumann",))
            kind = spec[0]
            self.wall_kind[c].set(kind)
            self.wall_p1[c].set(round(spec[1], 4) if kind == "dirichlet" else 0.0)
            self._maj_paroi(c)

    # ----------------------------------------------------------- obstacles
    def _ajouter_obstacle(self):
        forme = self.ob_forme.get()
        x, y, r = self.ob_x.get(), self.ob_y.get(), self.ob_r.get()
        T = self.ob_T.get()
        bc = ("dirichlet", T)
        if forme == "disque":
            args = {"cx": x, "cy": y, "r": r}
        else:
            args = {"x0": x - r, "y0": y - r, "x1": x + r, "y1": y + r}
        self.obstacles_th.append({"forme": forme, "args": args, "bc": bc})
        self.liste.insert("end", f"{forme} T={T:.1f}°C  ({x:.2f},{y:.2f}) t={r:.2f}")

    def _vider_obstacles(self):
        self.obstacles_th.clear()
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
        d["v"]         = float(self.var_T_chaud.get())
        d["walls"]     = self._walls()
        d["obstacles"] = list(self.obstacles_th)
