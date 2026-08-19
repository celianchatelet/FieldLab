import copy
import inspect

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from fieldlab.solvers import METHODES
from fieldlab.solvers.sor import omega_optimal
from fieldlab.sources import NOMS_FORMES
from fieldlab import viz
from fieldlab import geometries as geo
from fieldlab.geometries import NOM_SCENE_LIBRE_2D
from fieldlab.app.scene_editor_panel import SceneEditorPanel
from fieldlab.app.vtk_compat import THREE_D_AVAILABLE, fem3d_render
from fieldlab.app.vocabulaire_domaine import (
    aide_conditions_limites_3d, conditions_limites_3d,
    defauts_condition_limite_3d, libelle_condition_limite_3d,
    libelles_parametres_condition_limite_3d,
)

from fieldlab.app.widgets_i18n import ComboBoxTraduit as QComboBox
from fieldlab.i18n import tr
COTES = ["haut", "bas", "gauche", "droite"]
FACES_3D = (
    ("gauche", "X− · gauche"), ("droite", "X+ · droite"),
    ("avant", "Y− · avant"), ("arriere", "Y+ · arrière"),
    ("bas", "Z− · bas"), ("haut", "Z+ · haut"),
)
_PREFIXE_SCENE_LIBRE = "Scène libre"


def make_double_spin(default=0.0, minv=-1.0e6, maxv=1.0e6, decimals=4, step=1.0):
    s = QDoubleSpinBox()
    s.setRange(minv, maxv)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(default)
    return s


def make_int_spin(default, minv=1, maxv=2_000_000, step=1):
    s = QSpinBox()
    s.setRange(minv, maxv)
    s.setSingleStep(step)
    s.setValue(default)
    return s


class BasePanel(QWidget):
    SUPPORTE_3D = False
    SCENARIOS_3D: dict = {}





    EDITION_3D = True








    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        dom = controller.domaine
        self._mode_interface = "expert"
        self._widgets_experts = []
        self._defaut_magnetique_3d_applique = False
        self._boutons_placement_2d = []
        self._chargement_scene_2d = False
        self._chargement_parois_3d = False
        self._dernier_scenario_2d = None
        self._parois_scene_libre_2d = None

        self.spin_N = make_int_spin(120, minv=10, maxv=1000)
        self.cb_meth = QComboBox(); self.cb_meth.addItems(METHODES)





        self.cb_meth.setCurrentText("FEM (direct)")
        self.spin_omega = make_double_spin(1.9, 1.0, 1.99, decimals=3, step=0.01)
        self.spin_maxiter = make_int_spin(8000, minv=1, maxv=1_000_000, step=100)
        self.edit_tol = QLineEdit("1e-5")
        self.spin_refine = make_int_spin(0, minv=0, maxv=4, step=1)
        self.cb_viz = QComboBox(); self.cb_viz.addItems(viz.KINDS)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(8, 8, 8, 8)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, stretch=1)


        self.bottom = QWidget()
        bl = QVBoxLayout(self.bottom)
        bl.setContentsMargins(10, 6, 10, 6)
        actions = QHBoxLayout()
        self.run_btn = QPushButton("Lancer la simulation")
        self.run_btn.setToolTip(
            "Calcule le champ avec les paramètres affichés.")
        self.run_btn.clicked.connect(self._lancer_simulation)
        actions.addWidget(self.run_btn, stretch=2)
        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.controller.annuler)
        actions.addWidget(self.cancel_btn)
        self.reset_btn = QPushButton("Réinitialiser")
        self.reset_btn.clicked.connect(self.controller.reinitialiser)
        actions.addWidget(self.reset_btn)
        self._declarer_niveau(self.reset_btn, "expert")
        bl.addLayout(actions)
        self.progress = QProgressBar(); self.progress.setRange(0, 100)
        bl.addWidget(self.progress)
        self.status = QLabel("Prêt.")
        self.status.setStyleSheet("color: gray;")
        bl.addWidget(self.status)
        outer.addWidget(self.bottom)

        self._build(dom, self.body_layout)


    def _build(self, dom, layout):
        title = QLabel(dom.titre)
        f = title.font(); f.setPointSize(15); f.setBold(True); title.setFont(f)
        layout.addWidget(title)
        subtitle = QLabel(f"{dom.scalaire}  ·  {dom.champ}")
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)

        self.groupe_validite = QGroupBox("Cadre scientifique et limites")
        self.groupe_validite.setCheckable(True)
        self.groupe_validite.setChecked(False)
        validite_layout = QVBoxLayout(self.groupe_validite)
        self.label_validite = QLabel()
        self.label_validite.setWordWrap(True)
        self.label_validite.setStyleSheet("color: #a7b6cc;")
        validite_layout.addWidget(self.label_validite)
        self.label_validite.hide()
        self.groupe_validite.toggled.connect(
            self.label_validite.setVisible)
        layout.addWidget(self.groupe_validite)

        if self.SUPPORTE_3D:
            self._build_dimension_toggle(layout)





        self.conteneur_2d = QWidget()
        c2d = QVBoxLayout(self.conteneur_2d)
        c2d.setContentsMargins(0, 0, 0, 0)


        g = QGroupBox("Géométrie")
        gl = QVBoxLayout(g)
        self.cb_geom = QComboBox()
        self.cb_geom.setToolTip(
            "Choisissez une situation classique de cours prête à simuler.")
        self.cb_geom.addItems(self._scenarios_affiches(dom))
        self.cb_geom.currentTextChanged.connect(self._on_scenario_change)
        gl.addWidget(self.cb_geom)
        self.info_scenario_2d = QLabel()
        self.info_scenario_2d.setWordWrap(True)
        gl.addWidget(self.info_scenario_2d)




        self.spin_taille = make_double_spin(1.0, 0.001, 1000.0, decimals=3, step=0.1)
        self.spin_taille.setToolTip(
            "Longueur physique du côté du domaine, en mètres.")
        self._row(gl, "Taille du domaine (m)", self.spin_taille)
        self.spin_taille.valueChanged.connect(self._scene_2d_modifiee)
        c2d.addWidget(g)


        self._build_domain_params(c2d, dom)


        self._build_sources_obstacles(c2d, dom)


        self._build_walls(c2d, dom)




        s = QGroupBox("Avancé — solveur numérique")
        self.groupe_solveur = s
        s.setCheckable(True)
        s.setChecked(False)
        sl = QVBoxLayout(s)
        contenu_solveur = QWidget()
        cl = QVBoxLayout(contenu_solveur)
        cl.setContentsMargins(0, 0, 0, 0)
        info_solveur = QLabel(
            "Par défaut : FEM (direct) — précis, rapide, et seul à prendre en "
            "compte matériaux et parois convection/rayonnement/flux. Les "
            "solveurs itératifs (Jacobi, Gauss-Seidel, SOR) sont proposés à "
            "titre pédagogique.")
        info_solveur.setWordWrap(True)
        info_solveur.setStyleSheet("color: gray;")
        cl.addWidget(info_solveur)
        r = QHBoxLayout()
        r.addWidget(QLabel("Méthode"))
        r.addWidget(self.cb_meth)
        cl.addLayout(r)
        cl.addWidget(QLabel("Oméga (SOR)"))
        cl.addWidget(self.spin_omega)
        opt_btn = QPushButton("Oméga optimal")
        opt_btn.clicked.connect(self._omega_opt)
        cl.addWidget(opt_btn)
        self._row(cl, "Itér. max", self.spin_maxiter)
        self._row(cl, "Tolérance", self.edit_tol)
        self._row(cl, "Raffinement (FEM)", self.spin_refine)
        sl.addWidget(contenu_solveur)
        contenu_solveur.setVisible(False)
        s.toggled.connect(contenu_solveur.setVisible)
        c2d.addWidget(s)
        self._declarer_niveau(s, "expert")

        layout.addWidget(self.conteneur_2d)

        if self.SUPPORTE_3D:
            self._build_conteneur_3d(layout)


        vz = QGroupBox("Visualisation")
        vzl = QVBoxLayout(vz)
        if self.SUPPORTE_3D:
            self.label_scalaire_3d = QLabel("Grandeur affichée")
            self.cb_scalaire_3d = QComboBox()
            self.cb_scalaire_3d.addItems(list(fem3d_render.SCALAIRES_3D))
            self.cb_scalaire_3d.currentIndexChanged.connect(
                lambda: self._on_scalaire_3d_change(
                    self.cb_scalaire_3d.currentText()))
            vzl.addWidget(self.label_scalaire_3d)
            vzl.addWidget(self.cb_scalaire_3d)
            self.label_scalaire_3d.hide()
            self.cb_scalaire_3d.hide()
        vzl.addWidget(QLabel("Mode de rendu"))
        vzl.addWidget(self.cb_viz)
        self.cb_viz.currentIndexChanged.connect(
            lambda: self.controller.refresh_plot(self.cb_viz.currentText()))
        layout.addWidget(vz)

        layout.addStretch(1)

        if hasattr(self, "cb_regime"):
            self.cb_regime.currentTextChanged.connect(self._maj_validite)
        self._maj_validite()


        self._charger_parois()
        self._dernier_scenario_2d = self.cb_geom.currentText()
        self._maj_disponibilite_edition_2d()


    def _build_dimension_toggle(self, layout):
        d = QGroupBox("Dimension")
        dl = QVBoxLayout(d)
        info = QLabel("3D : scénarios sur un vrai maillage tétraédrique "
                       "(éléments finis). « Scène libre » permet de créer "
                       "l'environnement ; les scénarios prédéfinis sont verrouillés.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        dl.addWidget(info)
        self.cb_regime_3d = QComboBox()
        self.cb_regime_3d.addItems(["Stationnaire", "Transitoire"])
        self.cb_regime_3d.currentTextChanged.connect(self._maj_dynamique_3d)
        if self.controller.domaine.nom == "Thermique":
            self._row(dl, "Régime", self.cb_regime_3d)
        else:
            self.cb_regime_3d.hide()
        self.cb_dimension = QComboBox()
        self.cb_dimension.addItems(["2D", "3D"])
        if not THREE_D_AVAILABLE:
            item_3d = self.cb_dimension.model().item(1)
            if item_3d is not None:
                item_3d.setEnabled(False)
            self.cb_dimension.setItemData(
                1, "3D désactivée : Windows bloque le composant VTK.",
                Qt.ItemDataRole.ToolTipRole)
        self.cb_dimension.currentIndexChanged.connect(
            lambda: self._on_dimension_change(self.cb_dimension.currentText()))
        dl.addWidget(self.cb_dimension)
        layout.addWidget(d)

    def _build_conteneur_3d(self, layout):
        self.conteneur_3d = QWidget()
        c3 = QVBoxLayout(self.conteneur_3d)
        c3.setContentsMargins(0, 0, 0, 0)
        g3 = QGroupBox("Scénario 3D")
        g3l = QVBoxLayout(g3)
        self.cb_geom_3d = QComboBox()
        self.cb_geom_3d.addItems(list(self.SCENARIOS_3D.keys()))
        self.cb_geom_3d.currentTextChanged.connect(
            self._maj_disponibilite_edition_3d)
        self.cb_geom_3d.currentTextChanged.connect(self._apercu_scene_3d)
        self.cb_geom_3d.currentTextChanged.connect(self._maj_validite)
        g3l.addWidget(self.cb_geom_3d)
        self.spin_taille_3d = make_double_spin(
            1.0, 0.001, 1000.0, decimals=3, step=0.1)
        self._row(g3l, "Taille du domaine (m)", self.spin_taille_3d)
        self.spin_taille_3d.valueChanged.connect(
            self._taille_scenario_3d_changee)
        self.spin_N_3d = make_int_spin(16, minv=4, maxv=40)
        self._row(
            g3l, "Résolution (par arête)", self.spin_N_3d,
            niveau="expert")
        c3.addWidget(g3)
        self._build_dynamique_3d(c3)
        if self.controller.domaine.nom == "Thermique":
            self._build_environnement_3d(c3)
        self.cb_geom_3d.currentTextChanged.connect(self._maj_dynamique_3d)
        self._build_conditions_limites_3d(c3)
        self.editeur_scene_3d = SceneEditorPanel(
            self.controller.domaine.nom,
            callback_scene=self._scene_3d_modifiee)
        c3.addWidget(self.editeur_scene_3d)
        self._declarer_niveau(self.editeur_scene_3d, "expert")
        self._synchroniser_conditions_limites_3d()
        self.info_scenario_3d_verrouille = QLabel(
            "Scénario prédéfini : sa géométrie est définie par le modèle. "
            "Choisissez « Scène libre » pour ajouter, déplacer ou "
            "redimensionner des objets.")
        self.info_scenario_3d_verrouille.setWordWrap(True)
        self.info_scenario_3d_verrouille.setStyleSheet("color: #d97706;")
        c3.addWidget(self.info_scenario_3d_verrouille)
        self._maj_disponibilite_edition_3d()
        layout.addWidget(self.conteneur_3d)
        self.conteneur_3d.hide()

    def _build_dynamique_3d(self, layout):
        d = QGroupBox("Dynamique (transitoire / variable)")
        self.groupe_dynamique_3d = d
        dl = QVBoxLayout(d)
        info = QLabel("Paramètres temporels du scénario sélectionné. "
                       "Le pas de temps interne vaut durée/(images×5), "
                       "schéma implicite stable.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        dl.addWidget(info)
        self.spin_T_initiale_3d = make_double_spin(0.0)
        self.spin_duree_3d = make_double_spin(3600.0, 0.001, 1.0e10,
                                              decimals=3, step=60.0)
        self.spin_n_images_3d = make_int_spin(30, minv=2, maxv=500)
        self.cb_forme_temporelle_3d = QComboBox()
        self.cb_forme_temporelle_3d.addItems(NOMS_FORMES)
        self.spin_frequence_3d = make_double_spin(0.5, 0.001, 1.0e6,
                                                  decimals=3, step=0.1)
        self._lignes_dynamique_3d = {}
        for nom_param, libelle, widget in (
                ("T_initiale", "T initiale (°C)", self.spin_T_initiale_3d),
                ("duree", "Durée simulée (s)", self.spin_duree_3d),
                ("n_images", "Images", self.spin_n_images_3d),
                ("forme", "Forme", self.cb_forme_temporelle_3d),
                ("frequence", "Fréquence (Hz)", self.spin_frequence_3d)):
            ligne = QWidget()
            rl = QHBoxLayout(ligne)
            rl.setContentsMargins(0, 0, 0, 0)
            lab = QLabel(libelle)
            lab.setMinimumWidth(90)
            rl.addWidget(lab)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding,
                                 QSizePolicy.Policy.Fixed)
            rl.addWidget(widget)
            dl.addWidget(ligne)
            self._lignes_dynamique_3d[nom_param] = ligne
            if nom_param in {"n_images", "forme", "frequence"}:
                self._declarer_niveau(ligne, "expert")
        layout.addWidget(d)
        self._maj_dynamique_3d()

    def _build_conditions_limites_3d(self, layout):
        domaine_nom = self.controller.domaine.nom
        conditions = conditions_limites_3d(domaine_nom)
        self.groupe_parois_3d = None
        if not conditions:
            return

        groupe = QGroupBox("Conditions aux limites du domaine 3D")
        groupe.setCheckable(True)
        groupe.setChecked(False)
        self.groupe_parois_3d = groupe
        groupe_layout = QVBoxLayout(groupe)
        self.label_resume_parois_3d = QLabel()
        self.label_resume_parois_3d.setWordWrap(True)
        self.label_resume_parois_3d.setStyleSheet("color: #22c55e;")
        groupe_layout.addWidget(self.label_resume_parois_3d)
        aide = QLabel(aide_conditions_limites_3d(domaine_nom))
        aide.setWordWrap(True)
        aide.setStyleSheet("color: gray;")
        groupe_layout.addWidget(aide)

        self.contenu_parois_3d = QWidget()
        contenu_layout = QVBoxLayout(self.contenu_parois_3d)
        contenu_layout.setContentsMargins(0, 4, 0, 0)
        self.wall3d_kind = {}
        self.wall3d_p1 = {}
        self.wall3d_p2 = {}
        self.wall3d_lab1 = {}
        self.wall3d_lab2 = {}
        self.wall3d_ligne1 = {}
        self.wall3d_ligne2 = {}
        self._condition_precedente_3d = {}
        self._valeurs_conditions_3d = {}

        self._chargement_parois_3d = True
        try:
            for face, libelle_face in FACES_3D:
                face_box = QGroupBox(libelle_face)
                face_layout = QVBoxLayout(face_box)
                ligne_condition = QHBoxLayout()
                ligne_condition.addWidget(QLabel("Condition"))
                cb = QComboBox()
                cb.setMinimumContentsLength(22)
                for condition in conditions:
                    cb.addItem(
                        libelle_condition_limite_3d(domaine_nom, condition),
                        condition)
                ligne_condition.addWidget(cb, stretch=1)
                face_layout.addLayout(ligne_condition)

                spin1 = make_double_spin(0.0)
                spin2 = make_double_spin(0.0)
                ligne1, label1 = self._ligne_parametre_paroi_3d(
                    face_layout, spin1)
                ligne2, label2 = self._ligne_parametre_paroi_3d(
                    face_layout, spin2)
                contenu_layout.addWidget(face_box)

                self.wall3d_kind[face] = cb
                self.wall3d_p1[face] = spin1
                self.wall3d_p2[face] = spin2
                self.wall3d_lab1[face] = label1
                self.wall3d_lab2[face] = label2
                self.wall3d_ligne1[face] = ligne1
                self.wall3d_ligne2[face] = ligne2
                condition_initiale = cb.currentData()
                self._condition_precedente_3d[face] = condition_initiale
                self._valeurs_conditions_3d[face] = {
                    condition: defauts_condition_limite_3d(
                        domaine_nom, condition)
                    for condition in conditions
                }
                cb.currentIndexChanged.connect(
                    lambda _index, f=face: self._maj_paroi_3d(f))
                spin1.valueChanged.connect(
                    self._conditions_limites_3d_modifiees)
                spin2.valueChanged.connect(
                    self._conditions_limites_3d_modifiees)
                self._maj_paroi_3d(
                    face, restaurer_valeurs=False, notifier=False)
        finally:
            self._chargement_parois_3d = False

        groupe_layout.addWidget(self.contenu_parois_3d)
        self.contenu_parois_3d.hide()
        groupe.toggled.connect(self.contenu_parois_3d.setVisible)
        layout.addWidget(groupe)
        self._maj_resume_parois_3d()

    @staticmethod
    def _ligne_parametre_paroi_3d(layout, widget):
        ligne = QWidget()
        ligne_layout = QHBoxLayout(ligne)
        ligne_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel()
        label.setWordWrap(True)
        label.setMinimumWidth(145)
        ligne_layout.addWidget(label)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ligne_layout.addWidget(widget)
        layout.addWidget(ligne)
        return ligne, label

    def _maj_paroi_3d(self, face, restaurer_valeurs=True, notifier=True):
        if not hasattr(self, "wall3d_kind") or face not in self.wall3d_kind:
            return
        domaine_nom = self.controller.domaine.nom
        condition = self.wall3d_kind[face].currentData()
        precedente = self._condition_precedente_3d.get(face)
        spin1, spin2 = self.wall3d_p1[face], self.wall3d_p2[face]
        condition_changee = restaurer_valeurs and precedente != condition

        if condition_changee and precedente:
            self._valeurs_conditions_3d[face][precedente] = (
                spin1.value(), spin2.value())
        if domaine_nom == "Thermique" and condition in {"robin", "radiation"}:
            spin1.setRange(0.0, 1.0 if condition == "radiation" else 1.0e6)
            spin1.setSingleStep(0.05 if condition == "radiation" else 1.0)
        else:
            spin1.setRange(-1.0e6, 1.0e6)
            spin1.setSingleStep(1.0)
        if condition_changee:
            valeur1, valeur2 = self._valeurs_conditions_3d[face].get(
                condition,
                defauts_condition_limite_3d(domaine_nom, condition))
            for spin, valeur in ((spin1, valeur1), (spin2, valeur2)):
                ancien_blocage = spin.blockSignals(True)
                spin.setValue(float(valeur))
                spin.blockSignals(ancien_blocage)
        self._condition_precedente_3d[face] = condition

        libelle1, libelle2 = libelles_parametres_condition_limite_3d(
            domaine_nom, condition)
        self.wall3d_lab1[face].setText(tr(libelle1 or ""))
        self.wall3d_lab2[face].setText(tr(libelle2 or ""))
        self.wall3d_ligne1[face].setVisible(libelle1 is not None)
        self.wall3d_ligne2[face].setVisible(libelle2 is not None)
        self._maj_resume_parois_3d()
        if notifier:
            self._conditions_limites_3d_modifiees()

    def _maj_resume_parois_3d(self):
        if not getattr(self, "groupe_parois_3d", None):
            return
        domaine_nom = self.controller.domaine.nom
        comptes = {}
        for cb in self.wall3d_kind.values():
            condition = cb.currentData()
            comptes[condition] = comptes.get(condition, 0) + 1
        morceaux = [
            f"{nombre} × {libelle_condition_limite_3d(domaine_nom, condition)}"
            for condition, nombre in comptes.items()
        ]
        source = "Résumé : " + " · ".join(morceaux)
        self.label_resume_parois_3d.setProperty("_i18n_source_text", source)
        self.label_resume_parois_3d.setText(tr(source))
        self._synchroniser_conditions_limites_3d()

    def _conditions_limites_3d_productrices(self):
        return (hasattr(self, "wall3d_kind")
                and any(cb.currentData() != "neumann"
                        for cb in self.wall3d_kind.values()))

    def _conditions_limites_3d_ancrent_solution(self):
        return (hasattr(self, "wall3d_kind")
                and any(cb.currentData() in {
                    "dirichlet", "robin", "radiation"}
                    for cb in self.wall3d_kind.values()))

    def _synchroniser_conditions_limites_3d(self):
        editeur = getattr(self, "editeur_scene_3d", None)
        if editeur is not None:
            editeur.definir_conditions_limites(
                self._conditions_limites_3d_productrices(),
                self._conditions_limites_3d_ancrent_solution())

    def _conditions_limites_3d_modifiees(self, *_args):
        self._maj_resume_parois_3d()
        if self._chargement_parois_3d:
            return
        if (not hasattr(self, "cb_dimension")
                or self.cb_dimension.currentText() != "3D"
                or not self._est_scene_libre()):
            return
        self.controller._generation += 1
        self.controller.result = None
        self.progress.setValue(0)
        self._afficher_statut(
            "Conditions aux limites modifiées — relancez la simulation.")

    def _walls_3d(self):
        parois = {}
        for face, cb in getattr(self, "wall3d_kind", {}).items():
            condition = cb.currentData()
            valeur1 = float(self.wall3d_p1[face].value())
            valeur2 = float(self.wall3d_p2[face].value())
            if condition in {"dirichlet", "flux"}:
                parois[face] = (condition, valeur1)
            elif condition in {"robin", "radiation"}:
                parois[face] = (condition, valeur1, valeur2)
            else:
                parois[face] = ("neumann",)
        return parois

    def _maj_dynamique_3d(self, _nom=None):
        if not hasattr(self, "groupe_dynamique_3d"):
            return
        if self.controller.domaine.nom == "Thermique":
            transitoire = self.cb_regime_3d.currentText() == "Transitoire"
            for nom, ligne in self._lignes_dynamique_3d.items():
                ligne.setVisible(
                    transitoire and nom in ("T_initiale", "duree", "n_images"))
            self.groupe_dynamique_3d.setVisible(True)
            if hasattr(self, "label_validite"):
                self._maj_validite()
            return
        acceptes = {nom: self._scenario_3d_accepte(nom)
                    for nom in self._lignes_dynamique_3d}
        for nom, ligne in self._lignes_dynamique_3d.items():
            ligne.setVisible(acceptes[nom])
        self.groupe_dynamique_3d.setVisible(any(acceptes.values()))

    def _scene_3d_modifiee(self, scene, index_selectionne=-1, modifie=False):
        if hasattr(self, "spin_taille_3d"):
            self.spin_taille_3d.blockSignals(True)
            self.spin_taille_3d.setValue(float(np.max(scene.dimensions)))
            self.spin_taille_3d.blockSignals(False)
        if hasattr(self, "cb_dimension") \
                and self.cb_dimension.currentText() == "3D":
            if modifie:
                self.controller._generation += 1
                self.controller.result = None
                self.progress.setValue(0)
                self._afficher_statut(
                    "Scène modifiée — relancez la simulation.")
            self.controller.plot.afficher_scene_3d(
                scene, index_selectionne,
                self.editeur_scene_3d.selectionner_depuis_vue,
                self.editeur_scene_3d.appliquer_transformation_vue,
                self.editeur_scene_3d.mode_transformation)

    def _apercu_scene_3d(self, *_args):
        if hasattr(self, "editeur_scene_3d"):
            environnement = self._est_scene_libre()
            self.spin_taille_3d.setEnabled(not environnement)
            if not environnement:
                self.controller.plot.reset()
                return
            self._scene_3d_modifiee(
                self.editeur_scene_3d.scene,
                self.editeur_scene_3d.index_selectionne,
                modifie=False)

    def _taille_scenario_3d_changee(self, valeur):
        if not hasattr(self, "editeur_scene_3d") or not self._est_scene_libre():
            return
        editeur = self.editeur_scene_3d
        editeur._chargement_formulaire = True
        try:
            for spin in (editeur.spin_lx, editeur.spin_ly, editeur.spin_lz):
                spin.setValue(float(valeur))
            editeur.scene.taille_m = float(valeur)
            editeur.scene.boite_domaine = (
                (0.0, 0.0, 0.0), (float(valeur),) * 3)
        finally:
            editeur._chargement_formulaire = False
        self._apercu_scene_3d()









    def _on_dimension_change(self, texte):
        if texte == "3D" and not THREE_D_AVAILABLE:
            self.cb_dimension.blockSignals(True)
            self.cb_dimension.setCurrentText("2D")
            self.cb_dimension.blockSignals(False)
            texte = "2D"
        est_3d = (texte == "3D")
        self.conteneur_2d.setVisible(not est_3d)
        self.conteneur_3d.setVisible(est_3d)
        vue_courante = self.cb_viz.currentText()
        self.cb_viz.blockSignals(True)
        self.cb_viz.clear()
        nouvelles_vues = (list(fem3d_render.MODES_RENDU)
                           if est_3d else list(viz.KINDS))
        self.cb_viz.addItems(nouvelles_vues)
        appliquer_defaut_magnetique = (
            est_3d and self.controller.domaine.nom == "Magnetostatique"
            and not self._defaut_magnetique_3d_applique)
        if appliquer_defaut_magnetique:
            self.cb_viz.setCurrentText("Lignes de champ")
        elif vue_courante in nouvelles_vues:
            self.cb_viz.setCurrentText(vue_courante)
        self.cb_viz.blockSignals(False)
        self.label_scalaire_3d.setVisible(est_3d)
        self.cb_scalaire_3d.setVisible(est_3d)
        if appliquer_defaut_magnetique:
            self.cb_scalaire_3d.setCurrentText("Intensité du champ")
            self.controller.plot.configurer_defaut_magnetique_3d()
            self._defaut_magnetique_3d_applique = True
        if est_3d:
            self._apercu_scene_3d()
        else:
            self.controller.plot.btn_2d.setEnabled(True)
            self._maj_disponibilite_edition_2d()
            self._scene_2d_modifiee()
        self._maj_validite()

    def _on_scalaire_3d_change(self, selection):
        plot = getattr(self.controller, "plot", None)
        if plot is None:
            return
        plot.set_scalaire_3d(selection)
        self.controller.refresh_plot(self.cb_viz.currentText())

    def _scenario_3d_accepte(self, nom_parametre):
        if not hasattr(self, "cb_geom_3d"):
            return False
        builder = self.SCENARIOS_3D.get(self.cb_geom_3d.currentText())
        if builder is None:
            return False
        try:
            parametres = inspect.signature(builder).parameters
        except (TypeError, ValueError):
            return False
        return (nom_parametre in parametres
                or any(p.kind == inspect.Parameter.VAR_KEYWORD
                       for p in parametres.values()))

    def _est_scene_libre(self):
        return (hasattr(self, "cb_geom_3d")
                and self.cb_geom_3d.currentText().startswith(
                    _PREFIXE_SCENE_LIBRE))

    def _maj_disponibilite_edition_3d(self, _nom=None):
        libre = self._est_scene_libre()
        edition_visible = libre and self._mode_interface == "expert"
        if hasattr(self, "editeur_scene_3d"):
            self.editeur_scene_3d.setVisible(edition_visible)
        groupe_parois = getattr(self, "groupe_parois_3d", None)
        if groupe_parois is not None:
            groupe_parois.setVisible(edition_visible)
        if hasattr(self, "info_scenario_3d_verrouille"):
            self.info_scenario_3d_verrouille.setVisible(not libre)
            if not libre:
                from fieldlab.scenarios_pedagogiques import description_scenario
                self.info_scenario_3d_verrouille.setText(
                    description_scenario(self.cb_geom_3d.currentText()))


    def _scenarios_affiches(self, dom):
        if self._mode_interface == "expert":
            return list(dom.scenarios)
        essentiels = getattr(dom, "scenarios_essentiels", ()) or ()
        if essentiels:
            return [n for n in essentiels if n in dom.scenarios]
        return [n for n in dom.scenarios if n != NOM_SCENE_LIBRE_2D]

    def _recharger_scenarios_mode(self):
        dom = self.controller.domaine
        courant = self.cb_geom.currentText()
        noms = self._scenarios_affiches(dom)
        bloque = self.cb_geom.blockSignals(True)
        self.cb_geom.clear()
        self.cb_geom.addItems(noms)
        if courant in noms:
            self.cb_geom.setCurrentText(courant)
        self.cb_geom.blockSignals(bloque)
        if self.SUPPORTE_3D and hasattr(self, "cb_geom_3d"):
            courant_3d = self.cb_geom_3d.currentText()
            noms_3d = list(self.SCENARIOS_3D)
            if self._mode_interface == "cours":
                noms_3d = [n for n in noms_3d
                           if not n.startswith(_PREFIXE_SCENE_LIBRE)]
            bloque = self.cb_geom_3d.blockSignals(True)
            self.cb_geom_3d.clear()
            self.cb_geom_3d.addItems(noms_3d)
            if courant_3d in noms_3d:
                self.cb_geom_3d.setCurrentText(courant_3d)
            self.cb_geom_3d.blockSignals(bloque)
        self._on_scenario_change()
        if self.SUPPORTE_3D:
            self._maj_disponibilite_edition_3d()

    def _declarer_niveau(self, widget, niveau):
        widget.setProperty("niveau_interface", niveau)
        if niveau == "expert" and widget not in self._widgets_experts:
            self._widgets_experts.append(widget)
        return widget

    def set_mode_interface(self, mode):
        """Applique un niveau de visibilité sans dupliquer les paramètres."""

        if mode not in {"cours", "expert"}:
            raise ValueError(f"Mode d'interface inconnu : {mode!r}")
        changement = mode != self._mode_interface
        self._mode_interface = mode
        if mode == "cours":
            self.cb_meth.setCurrentText("FEM (direct)")
            self.spin_N.setValue(100)
            self.spin_N_3d.setValue(14) if hasattr(self, "spin_N_3d") else None
            self.spin_refine.setValue(0)
            self.edit_tol.setText("1e-5")
        for widget in self._widgets_experts:
            widget.setVisible(mode == "expert")
        if changement:
            self._recharger_scenarios_mode()
        self._maj_disponibilite_edition_2d()
        if self.SUPPORTE_3D:
            self._maj_disponibilite_edition_3d()
        source = "Simuler" if mode == "cours" else "Lancer la simulation"
        self.run_btn.setProperty("_i18n_source_text", source)
        self.run_btn.setText(tr(source))

    def _build_domain_params(self, layout, dom):
        p = QGroupBox("Paramètres")
        pl = QVBoxLayout(p)
        self._row(pl, "Résolution N", self.spin_N, niveau="expert")
        layout.addWidget(p)

    def _build_sources_obstacles(self, layout, dom):
        pass

    def _build_walls(self, layout, dom):
        pass

    def _on_scenario_change(self, _text=None):
        nouveau = self.cb_geom.currentText()
        if self._dernier_scenario_2d == NOM_SCENE_LIBRE_2D:
            self._parois_scene_libre_2d = copy.deepcopy(self._walls())
        self._chargement_scene_2d = True
        try:
            self._appliquer_preset_scenario_2d(nouveau)
            if (nouveau == NOM_SCENE_LIBRE_2D
                    and self._parois_scene_libre_2d is not None):
                self._appliquer_parois_2d(self._parois_scene_libre_2d)
            else:
                self._charger_parois()
        finally:
            self._chargement_scene_2d = False
        self._dernier_scenario_2d = nouveau
        self._maj_disponibilite_edition_2d()
        self._maj_validite()
        self._scene_2d_modifiee()

    def _appliquer_preset_scenario_2d(self, scenario):
        if self._mode_interface != "cours":
            return
        from fieldlab.scenarios_pedagogiques import preset_2d

        preset = preset_2d(self.controller.domaine.nom, scenario)
        if not preset:
            return
        if "taille" in preset:
            self.spin_taille.setValue(float(preset["taille"]))
        for nom_widget in ("spin_v", "spin_J", "spin_T_chaud"):
            widget = getattr(self, nom_widget, None)
            if widget is not None and "valeur" in preset:
                widget.setValue(float(preset["valeur"]))
        environnement = getattr(self, "cb_environnement", None)
        if environnement is not None and "environnement" in preset:
            environnement.setCurrentText(str(preset["environnement"]))
        if "viz" in preset and self.cb_viz.findText(preset["viz"]) >= 0:
            self.cb_viz.setCurrentText(preset["viz"])
        if hasattr(self, "cb_regime") and "regime" in preset:
            self.cb_regime.setCurrentText(str(preset["regime"]))
        if hasattr(self, "spin_T_initiale") and "T_initiale" in preset:
            self.spin_T_initiale.setValue(float(preset["T_initiale"]))
        if hasattr(self, "spin_duree") and "duree" in preset:
            self.spin_duree.setValue(float(preset["duree"]))
        if (hasattr(self, "cb_vitesse_lecture")
                and "vitesse_lecture" in preset):
            index = self.cb_vitesse_lecture.findData(
                int(preset["vitesse_lecture"]))
            if index >= 0:
                self.cb_vitesse_lecture.setCurrentIndex(index)

    def _appliquer_parois_2d(self, parois):
        for cote in COTES:
            specification = parois.get(cote, ("neumann",))
            self.wall_kind[cote].setCurrentText(specification[0])
            self.wall_p1[cote].setValue(
                float(specification[1]) if len(specification) > 1 else 0.0)
            if hasattr(self, "wall_p2") and cote in self.wall_p2:
                self.wall_p2[cote].setValue(
                    float(specification[2]) if len(specification) > 2 else 0.0)
            self._maj_paroi(cote)

    def _est_scene_libre_2d(self):
        return (hasattr(self, "cb_geom")
                and self.cb_geom.currentText() == NOM_SCENE_LIBRE_2D)

    def _maj_disponibilite_edition_2d(self):
        libre = self._est_scene_libre_2d()
        groupes = list(getattr(self, "groupes_edition_2d", []))
        groupe_unique = getattr(self, "groupe_edition_2d", None)
        if groupe_unique is not None:
            groupes.append(groupe_unique)
        groupe_parois = getattr(self, "groupe_parois_2d", None)
        if groupe_parois is not None:
            groupes.append(groupe_parois)
        groupe_solaire = getattr(self, "groupe_solaire_2d", None)
        if groupe_solaire is not None:
            groupes.append(groupe_solaire)
        for groupe in groupes:
            groupe.setVisible(libre and self._mode_interface == "expert")
        for bouton in self._boutons_placement_2d:
            if not libre and bouton.isChecked():
                bouton.setChecked(False)
        if libre:
            self.info_scenario_2d.setText(
                "Scène libre : ajoutez vos objets, sources et conditions "
                "aux limites, puis placez-les au clic dans l’aperçu.")
            self.info_scenario_2d.setStyleSheet("color: #22c55e;")
        else:
            from fieldlab.scenarios_pedagogiques import description_scenario
            self.info_scenario_2d.setText(
                description_scenario(self.cb_geom.currentText()))
            self.info_scenario_2d.setStyleSheet("color: #22c55e;")

    def _scene_2d_modifiee(self, *_args):
        if self._chargement_scene_2d:
            return
        plot = getattr(self.controller, "plot", None)
        if plot is None or (hasattr(self, "cb_dimension")
                            and self.cb_dimension.currentText() != "2D"):
            return
        try:
            p = self.read_params()
            champ = geo.build(
                self.controller.domaine.scenarios, p["geom"],
                min(160, max(40, p["N"])), p["v"], p["walls"],
                p["obstacles"], q=p.get("q"),
                kappa_fond=p.get("kappa_fond", 1.0),
                taille_domaine=p.get("taille_domaine", 1.0),
                rho_cp_fond=p.get("rho_cp_fond", 1.0),
                facteur_source=p.get("facteur_source", 1.0))
        except (KeyError, TypeError, ValueError):
            return
        self.controller._generation += 1
        self.controller.result = None
        self.progress.setValue(0)
        self._afficher_statut(
            "Environnement modifié — relancez la simulation.")
        plot.afficher_scene_2d(champ, p["geom"])

    def _maj_validite(self, *_args):
        dimension = (self.cb_dimension.currentText()
                     if self.SUPPORTE_3D and hasattr(self, "cb_dimension")
                     else "2D")
        if (dimension == "3D" and hasattr(self, "cb_regime_3d")
                and self.controller.domaine.nom == "Thermique"):
            regime = self.cb_regime_3d.currentText()
        else:
            regime = (self.cb_regime.currentText()
                      if hasattr(self, "cb_regime") else "Stationnaire")
        scenario = (self.cb_geom_3d.currentText()
                    if dimension == "3D" and hasattr(self, "cb_geom_3d")
                    else self.cb_geom.currentText()
                    if hasattr(self, "cb_geom") else "")
        commun = [
            f"Modèle : {dimension}, régime {regime.lower()}, scénario « {scenario} ».",
            "Les propriétés de matériaux sont des ordres de grandeur pédagogiques, "
            "pas des données certifiées de conception.",
        ]
        if self.controller.domaine.nom == "Electrostatique":
            commun += [
                "Approximation électrostatique/quasi-statique : induction et "
                "propagation électromagnétique non modélisées.",
                "Les métaux placés comme matériaux sont approchés par une très "
                "forte permittivité ; une électrode imposée représente mieux un "
                "conducteur idéal.",
                "Une paroi de Neumann impose un flux normal nul : ce n'est pas "
                "une frontière ouverte à l'infini.",
            ]
        elif self.controller.domaine.nom == "Magnetostatique":
            if dimension == "3D":
                commun += [
                    "Biot–Savart dans l'air/le vide pour des fils minces : valeurs "
                    "en teslas, sans noyau magnétique ni courant induit.",
                ]
            else:
                commun += [
                    "Coupe 2D supposée infinie dans la direction hors plan ; "
                    "J_z est en A/m², A_z en T·m et B en teslas ; le facteur "
                    "μ₀ est inclus dans l'équation.",
                    "Matériaux magnétiques linéaires : saturation, hystérésis et "
                    "courants de Foucault non modélisés.",
                ]
        else:
            commun += [
                "Conduction thermique uniquement dans le domaine ; convection et "
                "rayonnement n'agissent que sur les parois configurées.",
                "Le rayonnement est linéarisé autour de la température ambiante : "
                "prudence pour les écarts de température très élevés.",
            ]
            if regime == "Transitoire":
                commun.append(
                    "Le transitoire utilise ρ·cp et un schéma implicite ; le pas "
                    "de temps influence la précision, même si le schéma reste stable.")
        premiere_traduite = (
            f"{tr('Modèle')} : {dimension}, {tr('régime')} "
            f"{tr(regime).lower()}, {tr('scénario')} « {tr(scenario)} ».")
        texte_source = "\n• " + "\n• ".join(commun)
        lignes_traduites = [premiere_traduite]
        lignes_traduites.extend(tr(ligne) for ligne in commun[1:])
        self.label_validite.setProperty("_i18n_source_text", texte_source)
        self.label_validite.setText(
            "\n• " + "\n• ".join(lignes_traduites))

    def _charger_parois(self):
        pass


    def _bouton_placement_2d(self, layout, spin_x, spin_y, ajouter_fn):
        btn = QPushButton("Placer au clic sur la carte")
        btn.setCheckable(True)

        def _basculer(actif):
            if actif:
                def cb(x, y):
                    spin_x.setValue(round(x, 3))
                    spin_y.setValue(round(y, 3))
                    ajouter_fn()
                self.controller.plot.activer_placement_2d(cb)
                btn.setText(tr("Placement actif — cliquez sur la carte"))
            else:
                self.controller.plot.activer_placement_2d(None)
                btn.setText(tr("Placer au clic sur la carte"))

        btn.toggled.connect(_basculer)
        layout.addWidget(btn)
        self._boutons_placement_2d.append(btn)
        return btn

    def _afficher_statut(self, texte):
        self.status.setProperty("_i18n_source_text", texte)
        self.status.setText(tr(texte))

    def _row(self, layout, label, widget, niveau="cours"):
        ligne = QWidget()
        r = QHBoxLayout(ligne)
        r.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(label)
        lab.setMinimumWidth(90)
        r.addWidget(lab)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        r.addWidget(widget)
        layout.addWidget(ligne)
        self._declarer_niveau(ligne, niveau)
        return ligne

    def _omega_opt(self):
        self.spin_omega.setValue(round(omega_optimal(self.spin_N.value()), 3))





    def _maj_paroi(self, c):
        kind = self.wall_kind[c].currentText()
        self.wall_p1[c].setEnabled(kind == "dirichlet")
        self._scene_2d_modifiee()

    def _walls(self):
        d = {}
        for c in COTES:
            k = self.wall_kind[c].currentText()
            d[c] = (("dirichlet", float(self.wall_p1[c].value()))
                    if k == "dirichlet" else ("neumann",))
        return d


    def _build_environnement(self, layout):
        from fieldlab.environments import NOMS_ENVIRONNEMENTS
        e = QGroupBox("Environnement")
        el = QVBoxLayout(e)
        info = QLabel("Milieu ambiant qui remplit le domaine (hors obstacles/"
                       "matériaux placés explicitement) : modifie la "
                       "conductivité/permittivité/perméabilité de fond.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        el.addWidget(info)
        self.cb_environnement = QComboBox()
        self.cb_environnement.addItems(["(aucun, vide normalise)"] + NOMS_ENVIRONNEMENTS)
        self.cb_environnement.currentIndexChanged.connect(
            lambda: self._appliquer_environnement(
                self.cb_environnement.currentText()))
        self.cb_environnement.currentTextChanged.connect(
            self._scene_2d_modifiee)
        el.addWidget(self.cb_environnement)
        layout.addWidget(e)

    def _build_environnement_3d(self, layout):
        """Expose le milieu de fond en 3D thermique, où le panneau 2D est caché."""

        from fieldlab.environments import NOMS_ENVIRONNEMENTS
        e = QGroupBox("Milieu physique 3D")
        el = QVBoxLayout(e)
        info = QLabel(
            "Matériau qui remplit le volume hors objets. Il fixe κ et ρ·cp, "
            "donc l'échelle de temps physique du transitoire.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        el.addWidget(info)
        self.cb_environnement_3d = QComboBox()
        self.cb_environnement_3d.addItems(
            ["(aucun, vide normalise)"] + NOMS_ENVIRONNEMENTS)
        el.addWidget(self.cb_environnement_3d)
        layout.addWidget(e)

    def _appliquer_environnement(self, _nom):
        pass

    def _combo_environnement_actif(self):
        if (hasattr(self, "cb_dimension")
                and self.cb_dimension.currentText() == "3D"
                and hasattr(self, "cb_environnement_3d")):
            return self.cb_environnement_3d
        return getattr(self, "cb_environnement", None)

    def _kappa_fond(self):
        cb = self._combo_environnement_actif()
        if cb is None or cb.currentText().startswith("(aucun"):
            return 1.0
        from fieldlab.environments import ENVIRONNEMENTS
        from fieldlab.materials import MATERIAUX, kappa_pour_domaine
        env = ENVIRONNEMENTS[cb.currentText()]
        return kappa_pour_domaine(MATERIAUX[env.materiau_fond], self.controller.domaine.nom)

    def _rho_cp_fond(self):
        cb = self._combo_environnement_actif()
        if cb is None or cb.currentText().startswith("(aucun"):
            return 1.0
        from fieldlab.environments import ENVIRONNEMENTS
        from fieldlab.materials import MATERIAUX
        env = ENVIRONNEMENTS[cb.currentText()]
        return MATERIAUX[env.materiau_fond].rho_cp


    def _build_regime_variable(self, layout):
        r = QGroupBox("Régime")
        rl = QVBoxLayout(r)
        info = QLabel("Stationnaire : amplitude constante.\n"
                       "Variable : amplitude animée dans le temps (lecteur "
                       "temporel), par résolutions stationnaires successives "
                       "indépendantes (approximation quasi-statique).")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        rl.addWidget(info)
        self.cb_regime = QComboBox()
        self.cb_regime.addItems(["Stationnaire", "Variable"])
        rl.addWidget(self.cb_regime)
        self.cb_forme_temporelle = QComboBox()
        self.cb_forme_temporelle.addItems(NOMS_FORMES)
        self._row(rl, "Forme", self.cb_forme_temporelle)
        self.spin_frequence = make_double_spin(1.0, 0.001, 1.0e6, decimals=3, step=0.1)
        self._row(rl, "Fréquence (Hz)", self.spin_frequence)
        self.spin_duree_var = make_double_spin(2.0, 0.001, 1.0e6, decimals=3, step=0.5)
        self._row(rl, "Durée simulée (s)", self.spin_duree_var)
        self.spin_n_images_var = make_int_spin(60, minv=2, maxv=500)
        self._row(rl, "Images", self.spin_n_images_var)
        layout.addWidget(r)
        self._declarer_niveau(r, "expert")

    def _contribute_regime_variable(self, d):
        d["regime"] = self.cb_regime.currentText()
        d["forme_temporelle"] = self.cb_forme_temporelle.currentText()
        d["frequence"] = float(self.spin_frequence.value())
        d["duree"] = float(self.spin_duree_var.value())
        d["n_images"] = int(self.spin_n_images_var.value())


    def _vider_obstacles(self):
        pass

    def contribute_params(self, d):
        pass

    def read_params(self):
        d = {
            "geom":     self.cb_geom.currentText(),
            "N":        int(self.spin_N.value()),
            "method":   self.cb_meth.currentText(),
            "omega":    float(self.spin_omega.value()),
            "max_iter": int(self.spin_maxiter.value()),
            "tol":      float(self.edit_tol.text()),
            "viz":      self.cb_viz.currentText(),
            "refine":   int(self.spin_refine.value()),
            "kappa_fond": self._kappa_fond(),
            "taille_domaine": float(self.spin_taille.value()),
        }
        from fieldlab.constantes import facteur_source_poisson
        d["facteur_source"] = facteur_source_poisson(
            self.controller.domaine.nom)
        d["dimension"] = "2D"
        if self.SUPPORTE_3D and self.cb_dimension.currentText() == "3D":
            d["dimension"] = "3D"
            d["geom_3d"] = self.cb_geom_3d.currentText()
            d["N_3d"] = int(self.spin_N_3d.value())
            d["scalaire_3d"] = self.cb_scalaire_3d.currentText()
            d["regime_3d"] = self.cb_regime_3d.currentText()
            if self._est_scene_libre():
                d["scene_3d"] = self.editeur_scene_3d.scene
                if getattr(self, "groupe_parois_3d", None) is not None:
                    d["walls_3d"] = self._walls_3d()



            d["T_initiale_3d"] = float(self.spin_T_initiale_3d.value())
            d["duree_3d"] = float(self.spin_duree_3d.value())
            d["n_images_3d"] = int(self.spin_n_images_3d.value())
            d["forme_temporelle_3d"] = \
                self.cb_forme_temporelle_3d.currentText()
            d["frequence_3d"] = float(self.spin_frequence_3d.value())
            if self._scenario_3d_accepte("taille_m"):
                d["taille_m_3d"] = float(self.spin_taille_3d.value())
        self.contribute_params(d)
        environnement = self._combo_environnement_actif()
        d["environnement"] = (environnement.currentText()
                                if environnement is not None else "")
        if d["dimension"] == "2D" and not self._est_scene_libre_2d():
            d["obstacles"] = []
        return d

    def _lancer_simulation(self):
        if (not self.SUPPORTE_3D
                or self.cb_dimension.currentText() != "3D"
                or not self._est_scene_libre()):
            self.controller.run_simulation()
            return

        editeur = self.editeur_scene_3d
        produit_un_champ, message = editeur.scene_produit_un_champ()
        if produit_un_champ:
            if (self.controller.domaine.nom != "Magnetostatique"
                    and not editeur.scene_a_une_reference()):
                QMessageBox.warning(
                    self, tr("Référence physique manquante"),
                    tr(editeur.message_reference_manquante()))
                return
            self.controller.run_simulation()
            return

        scene_vide = not editeur.scene.items and not editeur.scene.circuits
        if scene_vide:
            QMessageBox.warning(
                self, tr("Scène 3D vide"),
                tr(message + "\n\nAjoutez au moins un élément physique avant de lancer."))
            return

        reponse = QMessageBox.question(
            self, tr("Champ trivial attendu"),
            tr(message + "\n\nLancer quand même ?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reponse == QMessageBox.StandardButton.Yes:
            self.controller.run_simulation()

    def set_running(self, running):
        self.run_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)

    def set_cancelling(self):
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

    def exporter_configuration(self):
        types_simples = (QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QCheckBox)

        def valeur(widget):
            if isinstance(widget, QComboBox):
                return {
                    "type": "combo",
                    "value": widget.currentText(),
                    "data": widget.currentData(),
                }
            if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                return {"type": "number", "value": widget.value()}
            if isinstance(widget, QLineEdit):
                return {"type": "text", "value": widget.text()}
            return {"type": "check", "value": widget.isChecked()}

        widgets = {}
        for nom, objet in vars(self).items():
            if isinstance(objet, types_simples):
                widgets[nom] = valeur(objet)
            elif isinstance(objet, dict):
                sous = {str(cle): valeur(w) for cle, w in objet.items()
                        if isinstance(w, types_simples)}
                if sous:
                    widgets[nom] = {"type": "mapping", "value": sous}
        configuration = {"widgets": widgets}
        scene_2d = {}
        for nom in ("obstacles", "obstacles_th", "sources", "noyaux"):
            valeur_scene = getattr(self, nom, None)
            if isinstance(valeur_scene, list):
                scene_2d[nom] = copy.deepcopy(valeur_scene)
        if scene_2d:
            configuration["scene_2d"] = scene_2d
        if self._parois_scene_libre_2d is not None:
            configuration.setdefault("scene_2d", {})["parois_libres"] = \
                copy.deepcopy(self._parois_scene_libre_2d)
        if hasattr(self, "editeur_scene_3d"):
            configuration["scene_3d"] = \
                self.editeur_scene_3d.scene.to_dict()
        return configuration

    def charger_configuration(self, configuration):
        types_simples = (QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QCheckBox)

        def appliquer(widget, donnees):
            if not isinstance(widget, types_simples) or not isinstance(donnees, dict):
                return
            ancienne = widget.blockSignals(True)
            try:
                valeur = donnees.get("value")
                if isinstance(widget, QComboBox):
                    donnee_interne = donnees.get("data", valeur)
                    index = (widget.findData(donnee_interne)
                             if donnee_interne is not None else -1)
                    if index < 0:
                        index = widget.findText(str(valeur))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(valeur))
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(valeur))
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(valeur))
                else:
                    widget.setChecked(bool(valeur))
            finally:
                widget.blockSignals(ancienne)

        for nom, donnees in (configuration.get("widgets") or {}).items():
            objet = getattr(self, nom, None)
            if isinstance(donnees, dict) and donnees.get("type") == "mapping":
                if isinstance(objet, dict):
                    for cle, etat in donnees.get("value", {}).items():
                        if cle in objet:
                            appliquer(objet[cle], etat)
            else:
                appliquer(objet, donnees)
        if hasattr(self, "wall3d_kind"):
            self._chargement_parois_3d = True
            try:
                for face in self.wall3d_kind:
                    self._maj_paroi_3d(
                        face, restaurer_valeurs=False, notifier=False)
            finally:
                self._chargement_parois_3d = False
            self._maj_resume_parois_3d()
        scene_2d = configuration.get("scene_2d") or {}
        self._parois_scene_libre_2d = copy.deepcopy(
            scene_2d.get("parois_libres"))
        self._chargement_scene_2d = True
        try:
            for nom in ("obstacles", "obstacles_th", "sources", "noyaux"):
                if nom in scene_2d and isinstance(getattr(self, nom, None), list):
                    setattr(self, nom, copy.deepcopy(scene_2d[nom]))
            if hasattr(self, "_rafraichir_obstacles"):
                self._rafraichir_obstacles()
            if hasattr(self, "_rafraichir_sources"):
                self._rafraichir_sources()
            if hasattr(self, "_rafraichir_noyaux"):
                self._rafraichir_noyaux()
        finally:
            self._chargement_scene_2d = False
        if configuration.get("scene_3d") and hasattr(self, "editeur_scene_3d"):
            from fieldlab.fem3d.scene import Scene3D
            editeur = self.editeur_scene_3d
            editeur.scene = Scene3D.from_dict(configuration["scene_3d"])
            editeur._charger_domaine()
            editeur._rafraichir_liste(
                0 if editeur.scene.items or editeur.scene.circuits else -1)
            editeur._enregistrer_historique()
        if self.SUPPORTE_3D and hasattr(self, "cb_dimension"):
            self._on_dimension_change(self.cb_dimension.currentText())
            self._maj_disponibilite_edition_3d()
            self._maj_dynamique_3d()
        self._dernier_scenario_2d = None
        self._on_scenario_change()
        self._maj_validite()
