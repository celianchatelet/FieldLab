import copy

from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QVBoxLayout,
)

from fieldlab.materials import MATERIAUX, NOMS_MATERIAUX, kappa_pour_domaine
from fieldlab.app.panels.base import BasePanel, COTES, make_double_spin
from fieldlab.fem3d.scenarios_magnetisme import SCENARIOS_3D_MAGNETISME

_FORMES_MAGNETO = ["fil (disque)", "barre (rectangle)"]
_FORMES_NOYAU = ["disque", "rectangle"]


class MagnetoPanel(BasePanel):
    SUPPORTE_3D = True
    SCENARIOS_3D = SCENARIOS_3D_MAGNETISME
    EDITION_3D = False

    def __init__(self, controller, parent=None):
        self.sources = []
        self.noyaux = []
        self.wall_kind = {}
        self.wall_p1 = {}
        super().__init__(controller, parent)


    def _build_domain_params(self, layout, dom):
        p = QGroupBox("Paramètres")
        pl = QVBoxLayout(p)
        self.spin_J = make_double_spin(dom.defaut)
        self._row(pl, "Courant J (A/m²)", self.spin_J)
        self._row(pl, "Résolution N", self.spin_N)
        layout.addWidget(p)
        self._build_environnement(layout)
        self._build_regime_variable(layout)

    def _build_sources_obstacles(self, layout, dom):
        o = QGroupBox("Sources de courant")
        self.groupes_edition_2d = [o]
        ol = QVBoxLayout(o)
        info = QLabel("Fil (disque-source) ou barre (rectangle-source) avec J signe.\n"
                       "+ = courant sortant (rouge) ;  - = courant entrant (bleu)")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        ol.addWidget(info)

        r1 = QHBoxLayout()
        self.cb_forme = QComboBox(); self.cb_forme.addItems(_FORMES_MAGNETO)
        self.cb_signe = QComboBox(); self.cb_signe.addItems(["+", "-"])
        r1.addWidget(self.cb_forme)
        r1.addWidget(self.cb_signe)
        ol.addLayout(r1)

        r2 = QHBoxLayout()
        self.spin_src_x = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_src_y = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_src_r = make_double_spin(0.05, 0.0, 1.0, decimals=3, step=0.01)
        self.spin_src_J = make_double_spin(20.0)
        for lab, w in (("x", self.spin_src_x), ("y", self.spin_src_y),
                       ("taille", self.spin_src_r), ("J", self.spin_src_J)):
            r2.addWidget(QLabel(lab))
            r2.addWidget(w)
        ol.addLayout(r2)

        r3 = QHBoxLayout()
        add_btn = QPushButton("Ajouter"); add_btn.clicked.connect(self._ajouter_source)
        update_btn = QPushButton("Mettre à jour")
        update_btn.clicked.connect(self._mettre_a_jour_source)
        duplicate_btn = QPushButton("Dupliquer")
        duplicate_btn.clicked.connect(self._dupliquer_source)
        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self._supprimer_source)
        clr_btn = QPushButton("Vider"); clr_btn.clicked.connect(self._vider_obstacles)
        for bouton in (add_btn, update_btn, duplicate_btn, delete_btn, clr_btn):
            r3.addWidget(bouton)
        ol.addLayout(r3)

        self._bouton_placement_2d(ol, self.spin_src_x, self.spin_src_y,
                                   self._ajouter_source)

        self.liste = QListWidget(); self.liste.setMaximumHeight(90)
        self.liste.currentRowChanged.connect(self._charger_source)
        ol.addWidget(self.liste)
        layout.addWidget(o)

        n = QGroupBox("Noyaux (matériaux)")
        self.groupes_edition_2d.append(n)
        nl = QVBoxLayout(n)
        info_n = QLabel("Objet rempli d'un materiau reel (fer/acier : concentrent le\n"
                         "flux ; autres materiaux : sans effet magnetique).")
        info_n.setWordWrap(True)
        info_n.setStyleSheet("color: gray;")
        nl.addWidget(info_n)

        r1n = QHBoxLayout()
        self.cb_forme_noyau = QComboBox(); self.cb_forme_noyau.addItems(_FORMES_NOYAU)
        self.cb_materiau_noyau = QComboBox(); self.cb_materiau_noyau.addItems(NOMS_MATERIAUX)
        self.cb_materiau_noyau.setCurrentText("Fer")
        r1n.addWidget(self.cb_forme_noyau)
        r1n.addWidget(self.cb_materiau_noyau)
        nl.addLayout(r1n)

        r2n = QHBoxLayout()
        self.spin_noyau_x = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_noyau_y = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_noyau_r = make_double_spin(0.1, 0.0, 1.0, decimals=3, step=0.01)
        for lab, w in (("x", self.spin_noyau_x), ("y", self.spin_noyau_y),
                       ("taille", self.spin_noyau_r)):
            r2n.addWidget(QLabel(lab))
            r2n.addWidget(w)
        nl.addLayout(r2n)

        r3n = QHBoxLayout()
        add_btn_n = QPushButton("Ajouter"); add_btn_n.clicked.connect(self._ajouter_noyau)
        update_btn_n = QPushButton("Mettre à jour")
        update_btn_n.clicked.connect(self._mettre_a_jour_noyau)
        duplicate_btn_n = QPushButton("Dupliquer")
        duplicate_btn_n.clicked.connect(self._dupliquer_noyau)
        delete_btn_n = QPushButton("Supprimer")
        delete_btn_n.clicked.connect(self._supprimer_noyau)
        clr_btn_n = QPushButton("Vider"); clr_btn_n.clicked.connect(self._vider_noyaux)
        for bouton in (add_btn_n, update_btn_n, duplicate_btn_n,
                       delete_btn_n, clr_btn_n):
            r3n.addWidget(bouton)
        nl.addLayout(r3n)

        self.liste_noyaux = QListWidget(); self.liste_noyaux.setMaximumHeight(90)
        self.liste_noyaux.currentRowChanged.connect(self._charger_noyau)
        nl.addWidget(self.liste_noyaux)
        layout.addWidget(n)

    def _build_walls(self, layout, dom):
        w = QGroupBox("Parois du domaine")
        self.groupe_parois_2d = w
        wl = QVBoxLayout(w)
        info = QLabel("A_z = 0 (Dirichlet) confine le flux dans la boite.\n"
                       "Passer en Neumann pour laisser le champ sortir.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #b05000;")
        wl.addWidget(info)

        grid = QGridLayout()
        for col, txt in ((0, "Cote"), (1, "Condition"), (2, "A_z")):
            lab = QLabel(txt); f = lab.font(); f.setBold(True); lab.setFont(f)
            grid.addWidget(lab, 0, col)
        for i, c in enumerate(COTES, start=1):
            grid.addWidget(QLabel(c.capitalize()), i, 0)
            cb = QComboBox(); cb.addItems(["dirichlet", "neumann"])
            cb.currentTextChanged.connect(lambda _t, k=c: self._maj_paroi(k))
            grid.addWidget(cb, i, 1)
            self.wall_kind[c] = cb
            spin = make_double_spin(0.0)
            spin.valueChanged.connect(self._scene_2d_modifiee)
            grid.addWidget(spin, i, 2)
            self.wall_p1[c] = spin
        wl.addLayout(grid)
        layout.addWidget(w)
        for c in COTES:
            self._maj_paroi(c)


    def _charger_parois(self):
        dom = self.controller.domaine
        val = self.spin_J.value() if hasattr(self, "spin_J") else dom.defaut
        walls = dom.walls_defaut(self.cb_geom.currentText(), val)
        for c in COTES:
            spec = walls.get(c, ("dirichlet", 0.0))
            self.wall_kind[c].setCurrentText(spec[0])
            self.wall_p1[c].setValue(round(spec[1], 4) if spec[0] == "dirichlet" else 0.0)
            self._maj_paroi(c)


    @staticmethod
    def _centre_taille(objet):
        args = objet["args"]
        if "cx" in args:
            return args["cx"], args["cy"], args["r"]
        return ((args["x0"] + args["x1"]) / 2,
                (args["y0"] + args["y1"]) / 2,
                (args["x1"] - args["x0"]) / 2)

    def _source_formulaire(self):
        forme = self.cb_forme.currentText()
        x, y, r = self.spin_src_x.value(), self.spin_src_y.value(), self.spin_src_r.value()
        J = self.spin_src_J.value() * (1 if self.cb_signe.currentText() == "+" else -1)
        if "fil" in forme:
            args = {"cx": x, "cy": y, "r": r}
            forme_ob = "disque"
        else:
            args = {"x0": x - r, "y0": y - r, "x1": x + r, "y1": y + r}
            forme_ob = "rectangle"
        return {"forme": forme_ob, "args": args, "bc": ("source", J)}

    def _rafraichir_sources(self, selection=None):
        self.liste.blockSignals(True)
        self.liste.clear()
        for source in self.sources:
            x, y, taille = self._centre_taille(source)
            courant = float(source["bc"][1])
            forme = "fil" if source["forme"] == "disque" else "barre"
            self.liste.addItem(
                f"{forme} J={courant:+.3g} ({x:.2f},{y:.2f}) t={taille:.2f}")
        self.liste.blockSignals(False)
        if selection is not None and self.sources:
            self.liste.setCurrentRow(min(selection, len(self.sources) - 1))
        self._scene_2d_modifiee()

    def _ajouter_source(self):
        self.sources.append(self._source_formulaire())
        self._rafraichir_sources(len(self.sources) - 1)

    def _mettre_a_jour_source(self):
        index = self.liste.currentRow()
        if 0 <= index < len(self.sources):
            self.sources[index] = self._source_formulaire()
            self._rafraichir_sources(index)

    def _dupliquer_source(self):
        index = self.liste.currentRow()
        if 0 <= index < len(self.sources):
            self.sources.insert(index + 1, copy.deepcopy(self.sources[index]))
            self._rafraichir_sources(index + 1)

    def _supprimer_source(self):
        index = self.liste.currentRow()
        if 0 <= index < len(self.sources):
            self.sources.pop(index)
            self._rafraichir_sources(index)

    def _charger_source(self, index):
        if not 0 <= index < len(self.sources):
            return
        source = self.sources[index]
        x, y, taille = self._centre_taille(source)
        courant = float(source["bc"][1])
        self.cb_forme.setCurrentIndex(0 if source["forme"] == "disque" else 1)
        self.cb_signe.setCurrentText("+" if courant >= 0 else "-")
        self.spin_src_x.setValue(x)
        self.spin_src_y.setValue(y)
        self.spin_src_r.setValue(taille)
        self.spin_src_J.setValue(abs(courant))

    def _vider_obstacles(self):
        self.sources.clear()
        self.noyaux.clear()
        if hasattr(self, "liste"):
            self._rafraichir_sources()
        if hasattr(self, "liste_noyaux"):
            self._rafraichir_noyaux()


    def _noyau_formulaire(self):
        forme = self.cb_forme_noyau.currentText()
        x, y, r = self.spin_noyau_x.value(), self.spin_noyau_y.value(), self.spin_noyau_r.value()
        nom_materiau = self.cb_materiau_noyau.currentText()
        kappa_val = kappa_pour_domaine(MATERIAUX[nom_materiau], "Magnetostatique")
        bc = ("materiau", kappa_val)
        if forme == "disque":
            args = {"cx": x, "cy": y, "r": r}
        else:
            args = {"x0": x - r, "y0": y - r, "x1": x + r, "y1": y + r}
        return {"forme": forme, "args": args, "bc": bc,
                "materiau": nom_materiau}

    def _rafraichir_noyaux(self, selection=None):
        self.liste_noyaux.blockSignals(True)
        self.liste_noyaux.clear()
        for noyau in self.noyaux:
            x, y, taille = self._centre_taille(noyau)
            self.liste_noyaux.addItem(
                f"{noyau['forme']} {noyau.get('materiau', 'matériau')} "
                f"({x:.2f},{y:.2f}) t={taille:.2f}")
        self.liste_noyaux.blockSignals(False)
        if selection is not None and self.noyaux:
            self.liste_noyaux.setCurrentRow(
                min(selection, len(self.noyaux) - 1))
        self._scene_2d_modifiee()

    def _ajouter_noyau(self):
        self.noyaux.append(self._noyau_formulaire())
        self._rafraichir_noyaux(len(self.noyaux) - 1)

    def _mettre_a_jour_noyau(self):
        index = self.liste_noyaux.currentRow()
        if 0 <= index < len(self.noyaux):
            self.noyaux[index] = self._noyau_formulaire()
            self._rafraichir_noyaux(index)

    def _dupliquer_noyau(self):
        index = self.liste_noyaux.currentRow()
        if 0 <= index < len(self.noyaux):
            self.noyaux.insert(index + 1, copy.deepcopy(self.noyaux[index]))
            self._rafraichir_noyaux(index + 1)

    def _supprimer_noyau(self):
        index = self.liste_noyaux.currentRow()
        if 0 <= index < len(self.noyaux):
            self.noyaux.pop(index)
            self._rafraichir_noyaux(index)

    def _charger_noyau(self, index):
        if not 0 <= index < len(self.noyaux):
            return
        noyau = self.noyaux[index]
        x, y, taille = self._centre_taille(noyau)
        self.cb_forme_noyau.setCurrentText(noyau["forme"])
        self.spin_noyau_x.setValue(x)
        self.spin_noyau_y.setValue(y)
        self.spin_noyau_r.setValue(taille)
        nom = noyau.get("materiau")
        if nom:
            self.cb_materiau_noyau.setCurrentText(nom)

    def _vider_noyaux(self):
        self.noyaux.clear()
        if hasattr(self, "liste_noyaux"):
            self._rafraichir_noyaux()


    def contribute_params(self, d):
        d["v"]         = float(self.spin_J.value())
        d["walls"]     = self._walls()
        d["obstacles"] = list(self.sources) + list(self.noyaux)
        self._contribute_regime_variable(d)
