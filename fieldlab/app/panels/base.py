"""Panneau de base commun a tous les domaines.

Contient : titre, selecteur de scenario, resolution N, solveur, visualisation,
barre d'action figee en bas (Lancer / Reinitialiser / progression / statut).

Les sous-classes (ElectrostatiquePanel, MagnetoPanel, ThermiquePanel) surchargent :
  _build_domain_params(host, dom) : section "Parametres" propre au domaine
  _build_sources_obstacles(host, dom) : section sources / obstacles / fils
  _build_walls(host, dom) : section "Parois"
  _charger_parois(event) : charge les valeurs par defaut du scenario courant
  contribute_params(d) : ajoute les cles propres au domaine dans le dict de
                         read_params() (v, walls, obstacles, q, ...)
  _vider_obstacles() : remet a zero la liste de sources/obstacles
"""
import tkinter as tk
from tkinter import ttk

from fieldlab.solvers import METHODES
from fieldlab.solvers.sor import omega_optimal
from fieldlab.app.widgets import ScrollableFrame
from fieldlab import viz

COTES = ["haut", "bas", "gauche", "droite"]


class BasePanel(ttk.Frame):
    """Panneau de controle de base (un domaine fixe)."""

    def __init__(self, master, page):
        super().__init__(master)
        self.page = page
        dom = page.domaine

        self.var_geom = tk.StringVar(value=next(iter(dom.scenarios)))
        self.var_N = tk.IntVar(value=120)
        self.var_meth = tk.StringVar(value="SOR")
        self.var_omega = tk.DoubleVar(value=1.9)
        self.var_maxiter = tk.IntVar(value=8000)
        self.var_tol = tk.StringVar(value="1e-5")
        self.var_viz = tk.StringVar(value=viz.KINDS[0])

        # Barre d'action figee en bas (creee avant le scroll pour toujours etre visible)
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

        # Zone defilante (haut)
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(side="top", fill="both", expand=True)

        self._build(dom, self.scroll.body)

    # ------------------------------------------------------------------ build
    def _build(self, dom, host):
        ttk.Label(host, text=dom.nom, font=("", 15, "bold")).pack(anchor="w")
        ttk.Label(host, text=f"{dom.scalaire}  -  {dom.champ}",
                  foreground="gray").pack(anchor="w", pady=(0, 6))

        # Geometrie / scenario
        g = ttk.LabelFrame(host, text="Geometrie", padding=6)
        g.pack(fill="x", pady=3)
        cbg = ttk.Combobox(g, textvariable=self.var_geom, values=list(dom.scenarios),
                           state="readonly")
        cbg.pack(fill="x")
        cbg.bind("<<ComboboxSelected>>", self._on_scenario_change)

        # Parametres propres au domaine (surcharger dans les sous-classes)
        self._build_domain_params(host, dom)

        # Sources / obstacles propres au domaine
        self._build_sources_obstacles(host, dom)

        # Parois propres au domaine
        self._build_walls(host, dom)

        # Solveur (commun)
        s = ttk.LabelFrame(host, text="Solveur", padding=6)
        s.pack(fill="x", pady=3)
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

        # Visualisation (commune)
        vz = ttk.LabelFrame(host, text="Visualisation", padding=6)
        vz.pack(fill="x", pady=3)
        cb = ttk.Combobox(vz, textvariable=self.var_viz, values=viz.KINDS,
                          state="readonly")
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>",
                lambda e: self.page.plot.redraw(self.var_viz.get()))

        # Charge les parois du scenario initial
        self._charger_parois()

    # ----------------------------------------- hooks pour les sous-classes
    def _build_domain_params(self, host, dom):
        """Section Parametres. Surcharger pour ajouter les champs specifiques."""
        p = ttk.LabelFrame(host, text="Parametres", padding=6)
        p.pack(fill="x", pady=3)
        self._row(p, "Resolution N", self.var_N)

    def _build_sources_obstacles(self, host, dom):
        """Section Sources/Obstacles. Surcharger selon le domaine."""

    def _build_walls(self, host, dom):
        """Section Parois. Surcharger selon le domaine."""

    def _on_scenario_change(self, event=None):
        self._charger_parois(event)

    def _charger_parois(self, event=None):
        """Charge les parois recommandees du scenario courant. Surcharger."""

    # ------------------------------------------------------- helpers communs
    def _row(self, parent, label, var):
        r = ttk.Frame(parent); r.pack(fill="x", pady=1)
        ttk.Label(r, text=label, width=12).pack(side="left")
        ttk.Entry(r, textvariable=var, width=10).pack(side="right")

    def _omega_opt(self):
        self.var_omega.set(round(omega_optimal(self.var_N.get()), 3))

    # ----------------------------------------- interface pour DomainPage
    def _vider_obstacles(self):
        """Vide la liste de sources/obstacles (surcharger si besoin)."""

    def contribute_params(self, d):
        """Sous-classes ajoutent leurs parametres propres dans d."""

    def read_params(self):
        d = {
            "geom":     self.var_geom.get(),
            "N":        int(self.var_N.get()),
            "method":   self.var_meth.get(),
            "omega":    float(self.var_omega.get()),
            "max_iter": int(self.var_maxiter.get()),
            "tol":      float(self.var_tol.get()),
            "viz":      self.var_viz.get(),
        }
        self.contribute_params(d)
        return d

    def set_running(self, running):
        self.run_btn.config(state="disabled" if running else "normal")
