import numpy as np

from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QVBoxLayout,
)

from fieldlab.app.widgets_i18n import ComboBoxTraduit as QComboBox
from fieldlab.materials import MATERIAUX, NOMS_MATERIAUX, kappa_pour_domaine
from fieldlab.app.panels.base import BasePanel, COTES, make_double_spin, make_int_spin
from fieldlab.app.vocabulaire_domaine import (
    libelle_parametre_2d, libelle_role,
)
from fieldlab.fem3d.scenarios_par_domaine import (
    NOM_SCENE_LIBRE, SCENARIOS_3D_THERMIQUE,
)
from fieldlab.unites import duree_diffusion_suggeree, format_duree
from fieldlab.i18n import tr

_FORMES_OB = ["disque", "rectangle"]
_PREFIXE_MATERIAU = "materiau : "
_LIBELLE_ELECTRODE = libelle_role("Thermique", "electrode")
_LIBELLE_MATERIAU = libelle_role("Thermique", "materiau")
_REGIMES = ["Stationnaire", "Transitoire"]

_TYPES_PAROI = ["neumann", "dirichlet", "robin", "radiation", "flux"]

_LIBELLES_PAROI = {
    "neumann":   ("", ""),
    "dirichlet": ("T (°C)", ""),
    "robin":     ("h (W/m².K)", "T∞ (°C)"),
    "radiation": ("ε (0-1)", "T∞ (°C)"),
    "flux":      ("q (W/m²)", ""),
}


def _scene_libre_thermique_ui(*args, walls=None, **kwargs):
    """Construit la scène puis applique les parois sans faux volumes source."""

    construire = SCENARIOS_3D_THERMIQUE[NOM_SCENE_LIBRE]
    champ = construire(*args, walls=None, **kwargs)
    if walls:
        from fieldlab.fem3d.scenarios import _appliquer_parois_cube
        _appliquer_parois_cube(champ, walls)
    return champ


_SCENARIOS_3D_THERMIQUE_UI = dict(SCENARIOS_3D_THERMIQUE)
_SCENARIOS_3D_THERMIQUE_UI[NOM_SCENE_LIBRE] = _scene_libre_thermique_ui


class ThermiquePanel(BasePanel):
    SUPPORTE_3D = True
    SCENARIOS_3D = _SCENARIOS_3D_THERMIQUE_UI

    def __init__(self, controller, parent=None):
        self.obstacles_th = []
        self.wall_kind = {}
        self.wall_p1 = {}
        self.wall_p2 = {}
        self.wall_lab1 = {}
        self.wall_lab2 = {}
        super().__init__(controller, parent)
        self._installer_controles_transitoires_3d()
        self.cb_regime.currentTextChanged.connect(
            lambda _texte: self._regime_transitoire_change("2D"))
        self.cb_regime_3d.currentTextChanged.connect(
            lambda _texte: self._regime_transitoire_change("3D"))
        for signal in (
                self.cb_environnement.currentTextChanged,
                self.spin_taille.valueChanged,
                self.cb_geom.currentTextChanged):
            signal.connect(self._recalculer_duree_suggeree_2d)
        for signal in (
                self.cb_environnement_3d.currentTextChanged,
                self.spin_taille_3d.valueChanged,
                self.cb_geom_3d.currentTextChanged):
            signal.connect(self._recalculer_duree_suggeree_3d)
        self._recalculer_duree_suggeree_2d(appliquer=False)
        self._recalculer_duree_suggeree_3d(appliquer=False)
        self._maj_honnetete_modele()


    def _build_domain_params(self, layout, dom):
        p = QGroupBox("Paramètres")
        pl = QVBoxLayout(p)
        self.spin_T_chaud = make_double_spin(dom.defaut)
        self.spin_T_chaud.setToolTip(
            "Température maintenue sur l'objet chaud, en degrés Celsius.")
        self._row(pl, libelle_parametre_2d("Thermique"), self.spin_T_chaud)
        self._row(pl, "Résolution N", self.spin_N, niveau="expert")
        layout.addWidget(p)

        r = QGroupBox("Régime")
        rl = QVBoxLayout(r)
        info = QLabel("Stationnaire : état d'équilibre final.\n"
                       "Transitoire : évolution dans le temps depuis la température "
                       "initiale (lecteur temporel). Les temps affichés sont "
                       "physiques (inertie ρ·cp réelle des matériaux et du "
                       "milieu ambiant ; milieu « aucun » = temps normalisé).")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        rl.addWidget(info)
        self.cb_regime = QComboBox()
        self.cb_regime.setToolTip(
            "Stationnaire montre l'équilibre; transitoire montre l'évolution réelle.")
        self.cb_regime.addItems(_REGIMES)
        rl.addWidget(self.cb_regime)
        self.spin_T_initiale = make_double_spin(0.0)
        self.spin_duree = make_double_spin(
            3600.0, 0.001, 1.0e10, decimals=3, step=60.0)
        self.spin_n_images = make_int_spin(60, minv=2, maxv=500)
        self.cb_vitesse_lecture = QComboBox()
        for vitesse in (1, 10, 100, 1000):
            self.cb_vitesse_lecture.addItem(f"×{vitesse}", vitesse)
        self.cb_vitesse_lecture.setCurrentIndex(
            self.cb_vitesse_lecture.findData(1000))
        self._row(rl, "T initiale (°C)", self.spin_T_initiale)
        self._row(rl, "Durée simulée (s)", self.spin_duree)
        self._row(rl, "Images", self.spin_n_images, niveau="expert")
        self._row(rl, "Vitesse de lecture", self.cb_vitesse_lecture)
        ligne_suggestion = QHBoxLayout()
        self.label_duree_suggeree = QLabel()
        self.label_duree_suggeree.setWordWrap(True)
        self.label_duree_suggeree.setStyleSheet("color: #22c55e;")
        ligne_suggestion.addWidget(self.label_duree_suggeree, stretch=1)
        self.btn_duree_suggeree = QPushButton("Durée suggérée")
        self.btn_duree_suggeree.clicked.connect(
            lambda: self._recalculer_duree_suggeree_2d(appliquer=True))
        ligne_suggestion.addWidget(self.btn_duree_suggeree)
        rl.addLayout(ligne_suggestion)
        self.label_conduction_pure = QLabel(
            "Conduction pure — la convection naturelle n'est pas modélisée : "
            "dans un fluide réel, le réchauffement serait plus rapide.")
        self.label_conduction_pure.setWordWrap(True)
        self.label_conduction_pure.setStyleSheet("color: #d97706;")
        rl.addWidget(self.label_conduction_pure)
        layout.addWidget(r)

        self._build_environnement(layout)

    def _installer_controles_transitoires_3d(self):
        layout = self.groupe_dynamique_3d.layout()
        self.cb_vitesse_lecture_3d = QComboBox()
        for vitesse in (1, 10, 100, 1000):
            self.cb_vitesse_lecture_3d.addItem(f"×{vitesse}", vitesse)
        self.cb_vitesse_lecture_3d.setCurrentIndex(
            self.cb_vitesse_lecture_3d.findData(1000))
        self._row(layout, "Vitesse de lecture", self.cb_vitesse_lecture_3d)
        ligne = QHBoxLayout()
        self.label_duree_suggeree_3d = QLabel()
        self.label_duree_suggeree_3d.setWordWrap(True)
        self.label_duree_suggeree_3d.setStyleSheet("color: #22c55e;")
        ligne.addWidget(self.label_duree_suggeree_3d, stretch=1)
        bouton = QPushButton("Durée suggérée")
        bouton.clicked.connect(
            lambda: self._recalculer_duree_suggeree_3d(appliquer=True))
        ligne.addWidget(bouton)
        layout.addLayout(ligne)
        self.label_conduction_pure_3d = QLabel(
            "Conduction pure — la convection naturelle n'est pas modélisée : "
            "dans un fluide réel, le réchauffement serait plus rapide.")
        self.label_conduction_pure_3d.setWordWrap(True)
        self.label_conduction_pure_3d.setStyleSheet("color: #d97706;")
        layout.addWidget(self.label_conduction_pure_3d)

    def connecter_lecteur(self, plot):
        """Synchronise les sélecteurs du panneau avec le lecteur de résultats."""

        combos = (self.cb_vitesse_lecture, self.cb_vitesse_lecture_3d)

        def appliquer(source):
            vitesse = int(source.currentData())
            plot.set_vitesse_lecture(vitesse)
            for combo in combos:
                if combo is source:
                    continue
                bloque = combo.blockSignals(True)
                combo.setCurrentIndex(combo.findData(vitesse))
                combo.blockSignals(bloque)

        for combo in combos:
            combo.currentIndexChanged.connect(
                lambda _index, source=combo: appliquer(source))
        appliquer(self.cb_vitesse_lecture)

    def _regime_transitoire_change(self, dimension):
        transitoire = ((self.cb_regime_3d.currentText()
                        if dimension == "3D" else self.cb_regime.currentText())
                       == "Transitoire")
        if transitoire:
            combo = (self.cb_environnement_3d if dimension == "3D"
                     else self.cb_environnement)
            if combo.currentText().startswith("(aucun"):
                combo.setCurrentText("Eau")
            if dimension == "3D":
                self._recalculer_duree_suggeree_3d(appliquer=True)
            else:
                self._recalculer_duree_suggeree_2d(appliquer=True)
        self._maj_honnetete_modele()

    def _duree_suggeree(self, dimension):
        combo = (self.cb_environnement_3d if dimension == "3D"
                 else self.cb_environnement)
        if combo.currentText().startswith("(aucun"):
            return None
        if dimension == "2D" and self._mode_interface == "cours":
            # Certains presets utilisent la longueur caractéristique de
            # l'objet (et non tout le domaine) : la trempe vise ainsi 45 min.
            from fieldlab.scenarios_pedagogiques import preset_2d
            preset = preset_2d(
                self.controller.domaine.nom, self.cb_geom.currentText())
            if "duree" in preset:
                return float(preset["duree"])
        from fieldlab.environments import ENVIRONNEMENTS
        env = ENVIRONNEMENTS[combo.currentText()]
        materiau = MATERIAUX[env.materiau_fond]
        taille = (self.spin_taille_3d.value() if dimension == "3D"
                  else self.spin_taille.value())
        return duree_diffusion_suggeree(
            taille, materiau.kappa_thermique, materiau.rho_cp)

    def _recalculer_duree_suggeree_2d(self, *_args, appliquer=True):
        duree = self._duree_suggeree("2D")
        if duree is None:
            self.label_duree_suggeree.setText(tr(
                "Sélectionnez un milieu pour calculer τ = L²/α."))
            return
        self.label_duree_suggeree.setText(tr(
            f"Suggestion ≈ {format_duree(duree)} (τ/4, conduction)."))
        if appliquer:
            self.spin_duree.setValue(duree)
        self._maj_honnetete_modele()

    def _recalculer_duree_suggeree_3d(self, *_args, appliquer=True):
        duree = self._duree_suggeree("3D")
        if duree is None:
            self.label_duree_suggeree_3d.setText(tr(
                "Sélectionnez un milieu pour calculer τ = L²/α."))
            return
        self.label_duree_suggeree_3d.setText(tr(
            f"Suggestion ≈ {format_duree(duree)} (τ/4, conduction)."))
        if appliquer:
            self.spin_duree_3d.setValue(duree)
        self._maj_honnetete_modele()

    def _maj_honnetete_modele(self):
        from fieldlab.environments import ENVIRONNEMENTS

        def est_fluide(combo):
            nom = combo.currentText()
            return (not nom.startswith("(aucun")
                    and ENVIRONNEMENTS[nom].materiau_fond
                    in {"Eau", "Huile", "Air"})

        self.label_conduction_pure.setVisible(
            self.cb_regime.currentText() == "Transitoire"
            and est_fluide(self.cb_environnement))
        self.label_conduction_pure_3d.setVisible(
            self.cb_regime_3d.currentText() == "Transitoire"
            and est_fluide(self.cb_environnement_3d))

    def _build_sources_obstacles(self, layout, dom):
        o = QGroupBox("Objets")
        self.groupe_edition_2d = o
        ol = QVBoxLayout(o)
        info = QLabel(
            f"{_LIBELLE_ELECTRODE} : bloc à T (°C) constante\n"
            f"{_LIBELLE_MATERIAU} : conductivité k réelle (solveur FEM)")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        ol.addWidget(info)

        r1 = QHBoxLayout()
        self.cb_forme = QComboBox(); self.cb_forme.addItems(_FORMES_OB)
        self.cb_type = QComboBox()
        self.cb_type.addItem(_LIBELLE_ELECTRODE, "temperature imposee")
        for nom in NOMS_MATERIAUX:
            self.cb_type.addItem(
                f"{_LIBELLE_MATERIAU} : {nom}",
                f"{_PREFIXE_MATERIAU}{nom}")
        r1.addWidget(self.cb_forme)
        r1.addWidget(self.cb_type)
        ol.addLayout(r1)

        r2 = QHBoxLayout()
        self.spin_ob_x = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_ob_y = make_double_spin(0.5, 0.0, 1.0, decimals=3, step=0.05)
        self.spin_ob_r = make_double_spin(0.1, 0.0, 1.0, decimals=3, step=0.01)
        self.spin_ob_T = make_double_spin(50.0)
        for lab, w in (("x", self.spin_ob_x), ("y", self.spin_ob_y),
                       ("taille", self.spin_ob_r), ("T (°C)", self.spin_ob_T)):
            r2.addWidget(QLabel(lab))
            r2.addWidget(w)
        ol.addLayout(r2)

        r3 = QHBoxLayout()
        add_btn = QPushButton("Ajouter"); add_btn.clicked.connect(self._ajouter_obstacle)
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

        self._bouton_placement_2d(ol, self.spin_ob_x, self.spin_ob_y,
                                   self._ajouter_obstacle)

        self.liste = QListWidget(); self.liste.setMaximumHeight(90)
        self.liste.currentRowChanged.connect(self._charger_obstacle)
        ol.addWidget(self.liste)
        layout.addWidget(o)

    def _build_walls(self, layout, dom):
        w = QGroupBox("Parois du domaine")
        self.groupe_parois_2d = w
        wl = QVBoxLayout(w)
        info = QLabel("neumann : isolée  ·  dirichlet : T imposée  ·  "
                       "robin : convection (h, T∞)  ·  radiation : rayonnement (ε, T∞)  ·  "
                       "flux : flux imposé (q, W/m², chauffage solaire par ex.) "
                       "— robin/radiation/flux : solveur FEM")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        wl.addWidget(info)

        grid = QGridLayout()
        for col, txt in ((0, "Cote"), (1, "Condition"), (2, "param 1"), (4, "param 2")):
            lab = QLabel(txt); f = lab.font(); f.setBold(True); lab.setFont(f)
            grid.addWidget(lab, 0, col)
        for i, c in enumerate(COTES, start=1):
            grid.addWidget(QLabel(c.capitalize()), i, 0)
            cb = QComboBox(); cb.addItems(_TYPES_PAROI)
            cb.currentTextChanged.connect(lambda _t, k=c: self._maj_paroi(k))
            grid.addWidget(cb, i, 1)
            self.wall_kind[c] = cb
            lab1 = QLabel(""); lab1.setStyleSheet("color: #555;")
            grid.addWidget(lab1, i, 2)
            self.wall_lab1[c] = lab1
            spin1 = make_double_spin(0.0)
            spin1.valueChanged.connect(self._scene_2d_modifiee)
            grid.addWidget(spin1, i, 3)
            self.wall_p1[c] = spin1
            lab2 = QLabel(""); lab2.setStyleSheet("color: #555;")
            grid.addWidget(lab2, i, 4)
            self.wall_lab2[c] = lab2
            spin2 = make_double_spin(0.0)
            spin2.valueChanged.connect(self._scene_2d_modifiee)
            grid.addWidget(spin2, i, 5)
            self.wall_p2[c] = spin2
        wl.addLayout(grid)
        layout.addWidget(w)
        for c in COTES:
            self._maj_paroi(c)

        self._build_solaire(layout)

    def _build_solaire(self, layout):
        s = QGroupBox("Rayonnement solaire (assistant)")
        self.groupe_solaire_2d = s
        sl = QVBoxLayout(s)
        info = QLabel("Calcule le flux absorbé q = α · flux solaire · cos(angle "
                       "d'incidence) et l'applique à la paroi choisie (type « flux »).")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        sl.addWidget(info)

        self.spin_flux_solaire = make_double_spin(1000.0, 0.0, 2000.0, decimals=1, step=50.0)
        self._row(sl, "Flux solaire (W/m²)", self.spin_flux_solaire)
        self.spin_angle_incidence = make_double_spin(0.0, 0.0, 90.0, decimals=1, step=5.0)
        self._row(sl, "Angle incidence (°)", self.spin_angle_incidence)
        self.spin_alpha_solaire = make_double_spin(0.9, 0.0, 1.0, decimals=2, step=0.05)
        self._row(sl, "Absorption α (0-1)", self.spin_alpha_solaire)

        self.label_flux_absorbe = QLabel("")
        sl.addWidget(self.label_flux_absorbe)
        for spin in (self.spin_flux_solaire, self.spin_angle_incidence, self.spin_alpha_solaire):
            spin.valueChanged.connect(self._maj_solaire)
        self._maj_solaire()

        r = QHBoxLayout()
        self.cb_cote_solaire = QComboBox(); self.cb_cote_solaire.addItems(COTES)
        appliquer_btn = QPushButton("Appliquer à cette paroi")
        appliquer_btn.clicked.connect(self._appliquer_solaire)
        r.addWidget(self.cb_cote_solaire)
        r.addWidget(appliquer_btn)
        sl.addLayout(r)
        layout.addWidget(s)

    def _maj_solaire(self):
        from fieldlab.solar import coefficient_reflexion, flux_absorbe
        q = flux_absorbe(self.spin_flux_solaire.value(), self.spin_angle_incidence.value(),
                          self.spin_alpha_solaire.value())
        rho = coefficient_reflexion(self.spin_alpha_solaire.value())
        self.label_flux_absorbe.setText(tr(
            f"Flux absorbé : {q:.1f} W/m²  (réflexion ρ = {rho:.2f})"))
        self._dernier_flux_solaire = q

    def _appliquer_solaire(self):
        c = self.cb_cote_solaire.currentText()
        self.wall_kind[c].setCurrentText("flux")
        self.wall_p1[c].setValue(getattr(self, "_dernier_flux_solaire", 0.0))
        self._maj_paroi(c)


    def _appliquer_environnement(self, nom):
        if nom.startswith("(aucun") or not self.wall_kind:
            return
        from fieldlab.environments import ENVIRONNEMENTS
        env = ENVIRONNEMENTS[nom]
        for c in COTES:
            if env.h_convection > 0:
                self.wall_kind[c].setCurrentText("robin")
                self.wall_p1[c].setValue(env.h_convection)
                self.wall_p2[c].setValue(env.t_ambiante)
            else:
                self.wall_kind[c].setCurrentText("radiation")
                self.wall_p1[c].setValue(env.emissivite)
                self.wall_p2[c].setValue(env.t_ambiante)
            self._maj_paroi(c)


    def _maj_paroi(self, c):
        kind = self.wall_kind[c].currentText()
        lab1, lab2 = _LIBELLES_PAROI.get(kind, ("", ""))
        self.wall_lab1[c].setText(tr(lab1))
        self.wall_lab2[c].setText(tr(lab2))
        self.wall_p1[c].setEnabled(bool(lab1))
        self.wall_p2[c].setEnabled(bool(lab2))
        self._scene_2d_modifiee()

    def _walls(self):
        d = {}
        for c in COTES:
            k = self.wall_kind[c].currentText()
            if k == "dirichlet":
                d[c] = ("dirichlet", float(self.wall_p1[c].value()))
            elif k in ("robin", "radiation"):
                d[c] = (k, float(self.wall_p1[c].value()), float(self.wall_p2[c].value()))
            elif k == "flux":
                d[c] = ("flux", float(self.wall_p1[c].value()))
            else:
                d[c] = ("neumann",)
        return d

    def _charger_parois(self):
        dom = self.controller.domaine
        val = self.spin_T_chaud.value() if hasattr(self, "spin_T_chaud") else dom.defaut
        walls = dom.walls_defaut(self.cb_geom.currentText(), val)
        for c in COTES:
            spec = walls.get(c, ("neumann",))
            self.wall_kind[c].setCurrentText(spec[0])
            self.wall_p1[c].setValue(round(spec[1], 4) if spec[0] == "dirichlet" else 0.0)
            self.wall_p2[c].setValue(0.0)
            self._maj_paroi(c)


    def _obstacle_formulaire(self):
        forme = self.cb_forme.currentText()
        x, y, r = self.spin_ob_x.value(), self.spin_ob_y.value(), self.spin_ob_r.value()
        type_sel = self.cb_type.currentData() or self.cb_type.currentText()
        if type_sel.startswith(_PREFIXE_MATERIAU):
            nom_materiau = type_sel[len(_PREFIXE_MATERIAU):]
            materiau = MATERIAUX[nom_materiau]
            kappa_val = kappa_pour_domaine(materiau, "Thermique")


            bc = ("materiau", kappa_val, materiau.rho_cp)
            libelle = self.cb_type.currentText()
        else:
            T = self.spin_ob_T.value()
            bc = ("dirichlet", T)
            libelle = f"T={T:.1f}°C"
        if forme == "disque":
            args = {"cx": x, "cy": y, "r": r}
        else:
            args = {"x0": x - r, "y0": y - r, "x1": x + r, "y1": y + r}
        return {"forme": forme, "args": args, "bc": bc, "libelle": libelle}

    def _rafraichir_obstacles(self, selection=None):
        self.liste.blockSignals(True)
        self.liste.clear()
        for obstacle in self.obstacles_th:
            args = obstacle["args"]
            if "cx" in args:
                x, y, taille = args["cx"], args["cy"], args["r"]
            else:
                x = (args["x0"] + args["x1"]) / 2
                y = (args["y0"] + args["y1"]) / 2
                taille = (args["x1"] - args["x0"]) / 2
            libelle = obstacle.get("libelle", obstacle["bc"][0])
            self.liste.addItem(
                f"{obstacle['forme']} {libelle} ({x:.2f},{y:.2f}) t={taille:.2f}")
        self.liste.blockSignals(False)
        if selection is not None and self.obstacles_th:
            self.liste.setCurrentRow(min(selection, len(self.obstacles_th) - 1))
        self._scene_2d_modifiee()

    def _ajouter_obstacle(self):
        self.obstacles_th.append(self._obstacle_formulaire())
        self._rafraichir_obstacles(len(self.obstacles_th) - 1)

    def _mettre_a_jour_obstacle(self):
        index = self.liste.currentRow()
        if 0 <= index < len(self.obstacles_th):
            self.obstacles_th[index] = self._obstacle_formulaire()
            self._rafraichir_obstacles(index)

    def _dupliquer_obstacle(self):
        import copy
        index = self.liste.currentRow()
        if 0 <= index < len(self.obstacles_th):
            self.obstacles_th.insert(
                index + 1, copy.deepcopy(self.obstacles_th[index]))
            self._rafraichir_obstacles(index + 1)

    def _supprimer_obstacle(self):
        index = self.liste.currentRow()
        if 0 <= index < len(self.obstacles_th):
            self.obstacles_th.pop(index)
            self._rafraichir_obstacles(index)

    def _charger_obstacle(self, index):
        if not 0 <= index < len(self.obstacles_th):
            return
        obstacle = self.obstacles_th[index]
        args, bc = obstacle["args"], obstacle["bc"]
        self.cb_forme.setCurrentText(obstacle["forme"])
        if "cx" in args:
            x, y, taille = args["cx"], args["cy"], args["r"]
        else:
            x = (args["x0"] + args["x1"]) / 2
            y = (args["y0"] + args["y1"]) / 2
            taille = (args["x1"] - args["x0"]) / 2
        self.spin_ob_x.setValue(x)
        self.spin_ob_y.setValue(y)
        self.spin_ob_r.setValue(taille)
        if bc[0] == "dirichlet":
            self.cb_type.setCurrentIndex(
                self.cb_type.findData("temperature imposee"))
            self.spin_ob_T.setValue(float(bc[1]))
        else:
            for nom, materiau in MATERIAUX.items():
                if np.isclose(kappa_pour_domaine(materiau, "Thermique"), bc[1]):
                    self.cb_type.setCurrentIndex(
                        self.cb_type.findData(_PREFIXE_MATERIAU + nom))
                    break

    def _vider_obstacles(self):
        self.obstacles_th.clear()
        if hasattr(self, "liste"):
            self._rafraichir_obstacles()


    def contribute_params(self, d):
        d["v"]          = float(self.spin_T_chaud.value())
        d["walls"]      = self._walls()
        d["obstacles"]  = list(self.obstacles_th)
        d["regime"]     = self.cb_regime.currentText()
        d["T_initiale"] = float(self.spin_T_initiale.value())
        d["duree"]      = float(self.spin_duree.value())
        d["n_images"]   = int(self.spin_n_images.value())
        d["rho_cp_fond"] = self._rho_cp_fond()
        combo_vitesse = (self.cb_vitesse_lecture_3d
                         if d.get("dimension") == "3D"
                         else self.cb_vitesse_lecture)
        d["vitesse_lecture"] = int(combo_vitesse.currentData())
