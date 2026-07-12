import numpy as np

from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QVBoxLayout,
)

from fieldlab.obstacles import FORMES
from fieldlab.materials import MATERIAUX, NOMS_MATERIAUX, kappa_pour_domaine
from fieldlab.app.panels.base import BasePanel, COTES, make_double_spin
from fieldlab.fem3d.scenarios_par_domaine import SCENARIOS_3D_ELECTROSTATIQUE

_PREFIXE_MATERIAU = "materiau : "
_TYPES_OBSTACLE = ["isolant", "conducteur"] + [
    f"{_PREFIXE_MATERIAU}{nom}" for nom in NOMS_MATERIAUX]


class ElectrostatiquePanel(BasePanel):
    SUPPORTE_3D = True
    SCENARIOS_3D = SCENARIOS_3D_ELECTROSTATIQUE

    def __init__(self, controller, parent=None):
        self.obstacles = []
        self.wall_kind = {}
        self.wall_p1 = {}
        super().__init__(controller, parent)


    def _build_domain_params(self, layout, dom):
        p = QGroupBox("Paramètres")
        pl = QVBoxLayout(p)
        self.spin_v = make_double_spin(dom.defaut)
        self._row(pl, "Tension (V)", self.spin_v)
        self._row(pl, "Résolution N", self.spin_N)
        layout.addWidget(p)
        self._build_environnement(layout)
        self._build_regime_variable(layout)

    def _build_sources_obstacles(self, layout, dom):
        o = QGroupBox("Obstacles")
        self.groupe_edition_2d = o
        ol = QVBoxLayout(o)
        info = QLabel("conducteur : tension V imposée  ·  isolant : bloque le champ\n"
                       "matériau : permittivité réelle (solveur FEM)")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        ol.addWidget(info)

        r1 = QHBoxLayout()
        self.cb_forme = QComboBox(); self.cb_forme.addItems(list(FORMES))
        self.cb_type = QComboBox(); self.cb_type.addItems(_TYPES_OBSTACLE)
        r1.addWidget(self.cb_forme)
        r1.addWidget(self.cb_type)
        ol.addLayout(r1)

        r2 = QHBoxLayout()
        self.spin_ob_x = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_ob_y = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_ob_r = make_double_spin(0.1, 0.0, 1.0, decimals=3, step=0.01)
        self.spin_ob_v = make_double_spin(5.0)
        for lab, w in (("x", self.spin_ob_x), ("y", self.spin_ob_y),
                       ("taille", self.spin_ob_r), ("V", self.spin_ob_v)):
            r2.addWidget(QLabel(lab))
            r2.addWidget(w)
        ol.addLayout(r2)

        r3 = QHBoxLayout()
        add_btn = QPushButton("Ajouter"); add_btn.clicked.connect(self._ajouter)
        update_btn = QPushButton("Mettre à jour")
        update_btn.clicked.connect(self._mettre_a_jour_obstacle)
        duplicate_btn = QPushButton("Dupliquer")
        duplicate_btn.clicked.connect(self._dupliquer_obstacle)
        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self._supprimer_obstacle)
        clr_btn = QPushButton("Vider"); clr_btn.clicked.connect(self._vider_obstacles)
        for bouton in (add_btn, update_btn, duplicate_btn, delete_btn, clr_btn):
            r3.addWidget(bouton)
        ol.addLayout(r3)

        self._bouton_placement_2d(ol, self.spin_ob_x, self.spin_ob_y, self._ajouter)

        self.liste = QListWidget(); self.liste.setMaximumHeight(90)
        self.liste.currentRowChanged.connect(self._charger_obstacle)
        ol.addWidget(self.liste)
        layout.addWidget(o)

    def _build_walls(self, layout, dom):
        w = QGroupBox("Parois du domaine")
        self.groupe_parois_2d = w
        wl = QVBoxLayout(w)
        info = QLabel("neumann : bord libre  ·  dirichlet : tension imposée (V)")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        wl.addWidget(info)

        grid = QGridLayout()
        for col, txt in ((0, "Cote"), (1, "Condition"), (2, "V")):
            lab = QLabel(txt); f = lab.font(); f.setBold(True); lab.setFont(f)
            grid.addWidget(lab, 0, col)
        for i, c in enumerate(COTES, start=1):
            grid.addWidget(QLabel(c.capitalize()), i, 0)
            cb = QComboBox(); cb.addItems(["neumann", "dirichlet"])
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
        val = self.spin_v.value() if hasattr(self, "spin_v") else dom.defaut
        walls = dom.walls_defaut(self.cb_geom.currentText(), val)
        for c in COTES:
            spec = walls.get(c, ("neumann",))
            self.wall_kind[c].setCurrentText(spec[0])
            self.wall_p1[c].setValue(round(spec[1], 4) if spec[0] == "dirichlet" else 0.0)
            self._maj_paroi(c)


    def _obstacle_formulaire(self):
        forme = self.cb_forme.currentText()
        x, y, r = self.spin_ob_x.value(), self.spin_ob_y.value(), self.spin_ob_r.value()
        type_sel = self.cb_type.currentText()
        if type_sel.startswith(_PREFIXE_MATERIAU):
            nom_materiau = type_sel[len(_PREFIXE_MATERIAU):]
            kappa_val = kappa_pour_domaine(MATERIAUX[nom_materiau], "Electrostatique")
            bc = ("materiau", kappa_val)
        elif type_sel == "isolant":
            bc = ("isolant",)
        else:
            bc = ("dirichlet", self.spin_ob_v.value())
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
        return {"forme": forme, "args": args, "bc": bc}

    def _description_obstacle(self, obstacle):
        forme, args, bc = obstacle["forme"], obstacle["args"], obstacle["bc"]
        if "cx" in args:
            x, y = args["cx"], args["cy"]
            taille = args.get("r", args.get("r_ext", 0.0))
        elif forme == "segment_v":
            x, y = args["x"], (args["y0"] + args["y1"]) / 2
            taille = (args["y1"] - args["y0"]) / 2
        else:
            x, y = (args["x0"] + args["x1"]) / 2, args.get(
                "y", (args.get("y0", 0.0) + args.get("y1", 0.0)) / 2)
            taille = (args["x1"] - args["x0"]) / 2
        return f"{forme} {bc[0]} ({x:.2f},{y:.2f}) t={taille:.2f}"

    def _rafraichir_obstacles(self, selection=None):
        self.liste.blockSignals(True)
        self.liste.clear()
        for obstacle in self.obstacles:
            self.liste.addItem(self._description_obstacle(obstacle))
        self.liste.blockSignals(False)
        if selection is not None and self.obstacles:
            self.liste.setCurrentRow(min(selection, len(self.obstacles) - 1))
        self._scene_2d_modifiee()

    def _ajouter(self):
        self.obstacles.append(self._obstacle_formulaire())
        self._rafraichir_obstacles(len(self.obstacles) - 1)

    def _mettre_a_jour_obstacle(self):
        index = self.liste.currentRow()
        if 0 <= index < len(self.obstacles):
            self.obstacles[index] = self._obstacle_formulaire()
            self._rafraichir_obstacles(index)

    def _dupliquer_obstacle(self):
        import copy
        index = self.liste.currentRow()
        if 0 <= index < len(self.obstacles):
            self.obstacles.insert(index + 1, copy.deepcopy(self.obstacles[index]))
            self._rafraichir_obstacles(index + 1)

    def _supprimer_obstacle(self):
        index = self.liste.currentRow()
        if 0 <= index < len(self.obstacles):
            self.obstacles.pop(index)
            self._rafraichir_obstacles(index)

    def _charger_obstacle(self, index):
        if not 0 <= index < len(self.obstacles):
            return
        obstacle = self.obstacles[index]
        forme, args, bc = obstacle["forme"], obstacle["args"], obstacle["bc"]
        self.cb_forme.setCurrentText(forme)
        if "cx" in args:
            x, y = args["cx"], args["cy"]
            taille = args.get("r", args.get("r_ext", 0.0))
        elif forme == "segment_v":
            x, y = args["x"], (args["y0"] + args["y1"]) / 2
            taille = (args["y1"] - args["y0"]) / 2
        else:
            x = (args["x0"] + args["x1"]) / 2
            y = args.get("y", (args.get("y0", 0.0) + args.get("y1", 0.0)) / 2)
            taille = (args["x1"] - args["x0"]) / 2
        self.spin_ob_x.setValue(x)
        self.spin_ob_y.setValue(y)
        self.spin_ob_r.setValue(taille)
        if bc[0] == "dirichlet":
            self.cb_type.setCurrentText("conducteur")
            self.spin_ob_v.setValue(float(bc[1]))
        elif bc[0] == "isolant":
            self.cb_type.setCurrentText("isolant")
        else:
            for nom, materiau in MATERIAUX.items():
                valeur = kappa_pour_domaine(materiau, "Electrostatique")
                if np.isclose(valeur, bc[1]):
                    self.cb_type.setCurrentText(_PREFIXE_MATERIAU + nom)
                    break

    def _vider_obstacles(self):
        self.obstacles.clear()
        if hasattr(self, "liste"):
            self._rafraichir_obstacles()


    def contribute_params(self, d):
        d["v"]         = float(self.spin_v.value())
        d["walls"]     = self._walls()
        d["obstacles"] = list(self.obstacles)
        self._contribute_regime_variable(d)
