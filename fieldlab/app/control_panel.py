import tkinter as tk
from tkinter import ttk

from fieldlab.solvers import METHODES
from fieldlab.solvers.sor import omega_optimal
from fieldlab.obstacles import FORMES
from fieldlab.app.widgets import ScrollableFrame
from fieldlab import viz

COTES = ["haut", "bas", "gauche", "droite"]

# Libelles des deux parametres selon le type de paroi (param1, param2)
PARAM_LABELS = {
    "neumann":   ("", ""),
    "dirichlet": ("val.", ""),
    "robin":     ("Biot", "T\u221e"),
    "radiation": ("R", "T\u221e"),
}


class ControlPanel(ttk.Frame):
    """Panneau de controle d'UNE page (un domaine fixe).

    Structure : zone defilante (tous les reglages) + barre d'action figee
    en bas (Lancer / Reinitialiser / progression / etat) toujours visible.
    """

    def __init__(self, master, page):
        super().__init__(master)
        self.page = page
        dom = page.domaine
        self.obstacles = []

        self.var_geom = tk.StringVar(value=next(iter(dom.scenarios)))
        self.var_v = tk.DoubleVar(value=dom.defaut)
        self.var_N = tk.IntVar(value=120)
        self.var_meth = tk.StringVar(value="SOR")
        self.var_omega = tk.DoubleVar(value=1.9)
        self.var_maxiter = tk.IntVar(value=8000)
        self.var_tol = tk.StringVar(value="1e-5")
        self.var_viz = tk.StringVar(value=viz.KINDS[0])
        self.wall_kind = {c: tk.StringVar(value="neumann") for c in COTES}
        self.wall_p1 = {c: tk.DoubleVar(value=0.0) for c in COTES}
        self.wall_p2 = {c: tk.DoubleVar(value=0.0) for c in COTES}
        self.wall_labA = {c: tk.StringVar(value="") for c in COTES}
        self.wall_labB = {c: tk.StringVar(value="") for c in COTES}
        self._wall_entA = {}
        self._wall_entB = {}
        self.ob_forme = tk.StringVar(value="disque")
        self.ob_x = tk.DoubleVar(value=0.5)
        self.ob_y = tk.DoubleVar(value=0.5)
        self.ob_r = tk.DoubleVar(value=0.1)
        self.ob_type = tk.StringVar(value="isolant")
        self.ob_v = tk.DoubleVar(value=5.0)

        # --- barre d'action figee (bas), creee avant le scroll ---
        self.bottom = ttk.Frame(self, padding=(10, 6))
        self.bottom.pack(side="bottom", fill="x")
        self.run_btn = ttk.Button(self.bottom, text="Lancer la simulation",
                                  command=self.page.run_simulation)
        self.run_btn.pack(fill="x", pady=(0, 3))
        ttk.Button(self.bottom, text="Reinitialiser",
                   command=self.page.reinitialiser).pack(fill="x", pady=(0, 3))
        self.progress = ttk.Progressbar(self.bottom, maximum=100)
        self.progress.pack(fill="x")
        self.status = ttk.Label(self.bottom, text="Pret.", foreground="gray")
        self.status.pack(anchor="w")

        # --- zone defilante (haut) ---
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(side="top", fill="both", expand=True)

        self._build(dom, self.scroll.body)

    # ------------------------------------------------------------------ build
    def _build(self, dom, host):
        ttk.Label(host, text=dom.nom, font=("", 15, "bold")).pack(anchor="w")
        ttk.Label(host, text=f"{dom.scalaire}  -  {dom.champ}",
                  foreground="gray").pack(anchor="w", pady=(0, 6))

        g = ttk.LabelFrame(host, text="Geometrie", padding=6); g.pack(fill="x", pady=3)
        cbg = ttk.Combobox(g, textvariable=self.var_geom, values=list(dom.scenarios),
                           state="readonly")
        cbg.pack(fill="x")
        cbg.bind("<<ComboboxSelected>>", self._charger_parois)

        p = ttk.LabelFrame(host, text="Parametres", padding=6); p.pack(fill="x", pady=3)
        r = ttk.Frame(p); r.pack(fill="x", pady=1)
        ttk.Label(r, text=dom.label_val).pack(side="left")
        ttk.Entry(r, textvariable=self.var_v, width=8).pack(side="right")
        self._row(p, "Resolution N", self.var_N)

        # --- Parois : en-tete + legende complete + 1 ligne/cote avec libelles dynamiques
        w = ttk.LabelFrame(host, text="Parois du domaine", padding=6); w.pack(fill="x", pady=3)
        ttk.Label(
            w, foreground="gray", justify="left", wraplength=300,
            text=("neumann : adiabatique  \u00b7  dirichlet : valeur impos\u00e9e  \u00b7  "
                  "robin : Biot + T\u221e (convection)  \u00b7  radiation : R + T\u221e"),
        ).pack(anchor="w", pady=(0, 4))

        grid = ttk.Frame(w); grid.pack(fill="x")
        for col, txt in ((0, "C\u00f4t\u00e9"), (1, "Condition"), (2, "param 1"), (4, "param 2")):
            ttk.Label(grid, text=txt, font=("", 8, "bold")).grid(
                row=0, column=col, sticky="w", padx=(0, 4), pady=(0, 2))
        for i, c in enumerate(COTES, start=1):
            ttk.Label(grid, text=c.capitalize()).grid(row=i, column=0, sticky="w", padx=(0, 4))
            cb = ttk.Combobox(grid, textvariable=self.wall_kind[c],
                              values=list(dom.wall_types), state="readonly", width=9)
            cb.grid(row=i, column=1, padx=(0, 8), pady=1)
            cb.bind("<<ComboboxSelected>>", lambda e, k=c: self._maj_paroi(k))
            ttk.Label(grid, textvariable=self.wall_labA[c], width=4,
                      foreground="#555").grid(row=i, column=2, sticky="e")
            eA = ttk.Entry(grid, textvariable=self.wall_p1[c], width=5)
            eA.grid(row=i, column=3, padx=(1, 8))
            ttk.Label(grid, textvariable=self.wall_labB[c], width=4,
                      foreground="#555").grid(row=i, column=4, sticky="e")
            eB = ttk.Entry(grid, textvariable=self.wall_p2[c], width=5)
            eB.grid(row=i, column=5, padx=1)
            self._wall_entA[c] = eA
            self._wall_entB[c] = eB

        o = ttk.LabelFrame(host, text="Obstacles", padding=6); o.pack(fill="x", pady=3)
        r1 = ttk.Frame(o); r1.pack(fill="x")
        ttk.Combobox(r1, textvariable=self.ob_forme, values=list(FORMES),
                     state="readonly", width=10).pack(side="left")
        ttk.Combobox(r1, textvariable=self.ob_type, values=["isolant", "conducteur"],
                     state="readonly", width=10).pack(side="left", padx=3)
        r2 = ttk.Frame(o); r2.pack(fill="x", pady=2)
        for lab, var in (("x", self.ob_x), ("y", self.ob_y), ("taille", self.ob_r),
                         ("V", self.ob_v)):
            ttk.Label(r2, text=lab).pack(side="left")
            ttk.Entry(r2, textvariable=var, width=5).pack(side="left", padx=2)
        r3 = ttk.Frame(o); r3.pack(fill="x")
        ttk.Button(r3, text="Ajouter", command=self._ajouter_obstacle).pack(side="left")
        ttk.Button(r3, text="Vider", command=self._vider_obstacles).pack(side="left", padx=3)
        self.liste = tk.Listbox(o, height=4); self.liste.pack(fill="x", pady=(3, 0))

        s = ttk.LabelFrame(host, text="Solveur", padding=6); s.pack(fill="x", pady=3)
        r = ttk.Frame(s); r.pack(fill="x")
        ttk.Label(r, text="Methode", width=10).pack(side="left")
        ttk.Combobox(r, textvariable=self.var_meth, values=METHODES,
                     state="readonly", width=14).pack(side="left")
        ttk.Label(s, text="Omega (SOR)").pack(anchor="w", pady=(3, 0))
        ttk.Scale(s, from_=1.0, to=1.99, variable=self.var_omega,
                  orient="horizontal").pack(fill="x")
        ttk.Button(s, text="Omega optimal", command=self._omega_opt).pack(anchor="w")
        self._row(s, "Iter. max", self.var_maxiter)
        self._row(s, "Tolerance", self.var_tol)

        vz = ttk.LabelFrame(host, text="Visualisation", padding=6); vz.pack(fill="x", pady=3)
        cb = ttk.Combobox(vz, textvariable=self.var_viz, values=viz.KINDS,
                          state="readonly"); cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>",
                lambda e: self.page.plot.redraw(self.var_viz.get()))

        self._charger_parois()

    # ------------------------------------------------------------- parois
    def _maj_paroi(self, c):
        """Met a jour les libelles et l'etat des champs selon le type de paroi."""
        la, lb = PARAM_LABELS.get(self.wall_kind[c].get(), ("", ""))
        self.wall_labA[c].set(la)
        self.wall_labB[c].set(lb)
        self._wall_entA[c].configure(state=("normal" if la else "disabled"))
        self._wall_entB[c].configure(state=("normal" if lb else "disabled"))

    def _charger_parois(self, event=None):
        """Charge les parois recommandees du scenario courant dans le panneau."""
        dom = self.page.domaine
        try:
            val = float(self.var_v.get())
        except (ValueError, tk.TclError):
            val = dom.defaut
        walls = dom.walls_defaut(self.var_geom.get(), val)
        for c in COTES:
            spec = walls.get(c, ("neumann",))
            self.wall_kind[c].set(spec[0])
            if spec[0] == "dirichlet":
                self.wall_p1[c].set(round(spec[1], 4)); self.wall_p2[c].set(0.0)
            elif spec[0] in ("robin", "radiation"):
                self.wall_p1[c].set(spec[1]); self.wall_p2[c].set(spec[2])
            else:
                self.wall_p1[c].set(0.0); self.wall_p2[c].set(0.0)
            self._maj_paroi(c)

    # ------------------------------------------------------------- helpers
    def _row(self, parent, label, var):
        r = ttk.Frame(parent); r.pack(fill="x", pady=1)
        ttk.Label(r, text=label, width=12).pack(side="left")
        ttk.Entry(r, textvariable=var, width=10).pack(side="right")

    def _omega_opt(self):
        self.var_omega.set(round(omega_optimal(self.var_N.get()), 3))

    def _ajouter_obstacle(self):
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
        else:  # segment_h
            args = {"y": y, "x0": x - r, "x1": x + r}
        self.obstacles.append({"forme": forme, "args": args, "bc": bc})
        self.liste.insert("end", f"{forme} {self.ob_type.get()} ({x:.2f},{y:.2f}) t={r:.2f}")

    def _vider_obstacles(self):
        self.obstacles.clear()
        self.liste.delete(0, "end")

    def _walls(self):
        d = {}
        for c in COTES:
            k = self.wall_kind[c].get()
            if k == "dirichlet":
                d[c] = ("dirichlet", float(self.wall_p1[c].get()))
            elif k == "robin":
                d[c] = ("robin", float(self.wall_p1[c].get()), float(self.wall_p2[c].get()))
            elif k == "radiation":
                d[c] = ("radiation", float(self.wall_p1[c].get()), float(self.wall_p2[c].get()))
            else:
                d[c] = ("neumann",)
        return d

    def read_params(self):
        return {
            "geom": self.var_geom.get(),
            "v": float(self.var_v.get()),
            "N": int(self.var_N.get()),
            "walls": self._walls(),
            "obstacles": list(self.obstacles),
            "method": self.var_meth.get(),
            "omega": float(self.var_omega.get()),
            "max_iter": int(self.var_maxiter.get()),
            "tol": float(self.var_tol.get()),
            "viz": self.var_viz.get(),
        }

    def set_running(self, running):
        self.run_btn.config(state="disabled" if running else "normal")
