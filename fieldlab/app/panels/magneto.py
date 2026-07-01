"""Panneau de controle du domaine magnetostatique.

Parametres : Courant J (A/m^2) pour les scenarios.
Sources    : fils (disque-source) ou barres (rectangle-source) avec J signe.
             Ces sources alimentent field.source (pas fixed_mask).
Parois     : A_z = 0 par defaut (Dirichlet, confine le flux dans la boite).
             Passer en Neumann pour laisser le champ sortir.

Note confinement A_z=0
----------------------
Le cadre Dirichlet A_z=0 sur les 4 bords est un choix de modelisation :
le flux magnetique est confine dans la boite. Pour un fil unique, cela
donne un champ qui ne ressemble pas au champ libre en 1/r.
Passer les parois en Neumann donne un comportement plus proche du champ libre.
"""
import tkinter as tk
from tkinter import ttk

from fieldlab.app.panels.base import BasePanel, COTES

_FORMES_MAGNETO = ["fil (disque)", "barre (rectangle)"]


class MagnetoPanel(BasePanel):

    def __init__(self, master, page):
        self.sources = []   # sources courant ajoutees par l'utilisateur
        self.wall_kind = {c: tk.StringVar(value="dirichlet") for c in COTES}
        self.wall_p1   = {c: tk.DoubleVar(value=0.0)         for c in COTES}
        self.wall_labA = {c: tk.StringVar(value="")          for c in COTES}
        self._wall_entA = {}
        self.var_J      = None   # cree dans _build_domain_params
        self.src_forme  = tk.StringVar(value="fil (disque)")
        self.src_x      = tk.DoubleVar(value=0.5)
        self.src_y      = tk.DoubleVar(value=0.5)
        self.src_r      = tk.DoubleVar(value=0.05)
        self.src_J      = tk.DoubleVar(value=20.0)
        self.src_signe  = tk.StringVar(value="+")
        super().__init__(master, page)

    # ------------------------------------------------------------------ build
    def _build_domain_params(self, host, dom):
        p = ttk.LabelFrame(host, text="Parametres", padding=6)
        p.pack(fill="x", pady=3)
        self.var_J = tk.DoubleVar(value=dom.defaut)
        r = ttk.Frame(p); r.pack(fill="x", pady=1)
        ttk.Label(r, text="Courant J (A/m²)").pack(side="left")
        ttk.Entry(r, textvariable=self.var_J, width=8).pack(side="right")
        self._row(p, "Resolution N", self.var_N)

    def _build_sources_obstacles(self, host, dom):
        o = ttk.LabelFrame(host, text="Sources de courant", padding=6)
        o.pack(fill="x", pady=3)
        ttk.Label(o, foreground="gray", justify="left", wraplength=300,
                  text="Fil (disque-source) ou barre (rectangle-source) avec J signe.\n"
                       "+ = courant sortant (rouge) ;  - = courant entrant (bleu)").pack(
            anchor="w", pady=(0, 4))
        r1 = ttk.Frame(o); r1.pack(fill="x")
        ttk.Combobox(r1, textvariable=self.src_forme, values=_FORMES_MAGNETO,
                     state="readonly", width=14).pack(side="left")
        ttk.Combobox(r1, textvariable=self.src_signe, values=["+", "-"],
                     state="readonly", width=3).pack(side="left", padx=3)
        r2 = ttk.Frame(o); r2.pack(fill="x", pady=2)
        for lab, var in (("x", self.src_x), ("y", self.src_y),
                         ("taille", self.src_r), ("J", self.src_J)):
            ttk.Label(r2, text=lab).pack(side="left")
            ttk.Entry(r2, textvariable=var, width=5).pack(side="left", padx=2)
        r3 = ttk.Frame(o); r3.pack(fill="x")
        ttk.Button(r3, text="Ajouter", command=self._ajouter_source).pack(side="left")
        ttk.Button(r3, text="Vider", command=self._vider_obstacles).pack(side="left", padx=3)
        self.liste = tk.Listbox(o, height=4)
        self.liste.pack(fill="x", pady=(3, 0))

    def _build_walls(self, host, dom):
        w = ttk.LabelFrame(host, text="Parois du domaine", padding=6)
        w.pack(fill="x", pady=3)
        ttk.Label(w, foreground="#b05000", justify="left", wraplength=300,
                  text="A_z = 0 (Dirichlet) confine le flux dans la boite.\n"
                       "Passer en Neumann pour laisser le champ sortir.").pack(
            anchor="w", pady=(0, 4))
        grid = ttk.Frame(w); grid.pack(fill="x")
        for col, txt in ((0, "Cote"), (1, "Condition"), (2, "A_z")):
            ttk.Label(grid, text=txt, font=("", 8, "bold")).grid(
                row=0, column=col, sticky="w", padx=(0, 4), pady=(0, 2))
        for i, c in enumerate(COTES, start=1):
            ttk.Label(grid, text=c.capitalize()).grid(row=i, column=0, sticky="w", padx=(0, 4))
            cb = ttk.Combobox(grid, textvariable=self.wall_kind[c],
                              values=["dirichlet", "neumann"],
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
        la = "A_z" if kind == "dirichlet" else ""
        self.wall_labA[c].set(la)
        self._wall_entA[c].configure(state=("normal" if la else "disabled"))

    def _charger_parois(self, event=None):
        dom = self.page.domaine
        try:
            val = float(self.var_J.get()) if self.var_J else dom.defaut
        except (ValueError, tk.TclError):
            val = dom.defaut
        walls = dom.walls_defaut(self.var_geom.get(), val)
        for c in COTES:
            spec = walls.get(c, ("dirichlet", 0.0))
            self.wall_kind[c].set(spec[0])
            self.wall_p1[c].set(round(spec[1], 4) if spec[0] == "dirichlet" else 0.0)
            self._maj_paroi(c)

    # ----------------------------------------------------------- sources
    def _ajouter_source(self):
        forme = self.src_forme.get()
        x, y, r = self.src_x.get(), self.src_y.get(), self.src_r.get()
        J = self.src_J.get() * (1 if self.src_signe.get() == "+" else -1)
        if "fil" in forme:
            args = {"cx": x, "cy": y, "r": r}
            forme_ob = "disque"
        else:
            args = {"x0": x - r, "y0": y - r, "x1": x + r, "y1": y + r}
            forme_ob = "rectangle"
        self.sources.append({"forme": forme_ob, "args": args, "bc": ("source", J)})
        sgn = self.src_signe.get()
        self.liste.insert(
            "end",
            f"{forme}  J={sgn}{self.src_J.get():.1f}  ({x:.2f},{y:.2f}) t={r:.2f}")

    def _vider_obstacles(self):
        self.sources.clear()
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
        d["v"]         = float(self.var_J.get())
        d["walls"]     = self._walls()
        d["obstacles"] = list(self.sources)
