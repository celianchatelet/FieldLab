from dataclasses import dataclass
from io import BytesIO
from time import monotonic

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)
from fieldlab import viz
from fieldlab.app import theme as theme_app
from fieldlab.app.vtk_compat import (
    THREE_D_AVAILABLE, QtInteractor, fem3d_render, viz3d, vtkCellPicker,
)
from fieldlab.app.widgets_i18n import ComboBoxTraduit as QComboBox
from fieldlab.i18n import tr
from fieldlab.fem3d.calques import MODES_GRAINES
from fieldlab.fem3d.coupe import fractions_plans, origine_plan_dans_bornes
from fieldlab.fem3d.field3d import Field3D
from fieldlab.fem3d.rendu_p3 import (
    abscisses_cumulees, superpositions_coupe_par_defaut,
)
from fieldlab.grid import Field
from fieldlab.unites import (
    format_duree, format_grandeur, unite_depuis_libelle,
)

_VITESSES_LECTURE = (1, 10, 100, 1000)
_TAILLES_EXPORT = {
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4K": (3840, 2160),
}


@dataclass
class _Instant:
    champ: Field


class PlotPanel(QWidget):
    def __init__(self, domaine, parent=None):
        super().__init__(parent)
        self.domaine = domaine
        self._dernier_resultat = None
        self._dernier_kind = None
        self._transitoire = None




        self._sonde_activee = False
        self._champ_3d_courant = None
        self._scalaire_sonde_3d = None
        self._observer_mouvement_3d = None
        self._dernier_mouvement_sonde = 0.0
        self._picker_sonde_3d = vtkCellPicker()
        self._picker_sonde_3d.SetTolerance(0.002)
        self._selection_scalaire_3d = "Scalaire principal"
        self._options_coupe_3d = fem3d_render.OptionsCoupe3D()
        self._options_rendu_3d = fem3d_render.OptionsRendu3D()



        self._calques_3d = fem3d_render.CalquesRendu3D()
        self._calques_2d = {
            "carte": True, "iso": False, "lignes": False, "fleches": False}
        self._fond_intensite_2d = False
        self._taille_apercu_2d = 1.0
        self._apercu_2d_courant = None
        self._theme_sombre = False
        self._bornes_plans_3d = None
        self._extremites_sonde_ligne_3d = None
        self._selection_scene_active = False
        self._correspondance_acteurs_scene = {}
        self._widget_affine_scene = None




        self._cb_placement_2d = None
        self._cid_placement = None
        self._cb_placement_3d = None
        self._sondes_2d = []
        self._points_profil_2d = []
        self._donnees_profil_2d = None


        self.btn_2d = QPushButton("Vue 2D")
        self.btn_2d.setCheckable(True)
        self.btn_2d.setChecked(True)
        self.btn_3d = QPushButton("Vue 3D")
        self.btn_3d.setCheckable(True)
        if not THREE_D_AVAILABLE:
            self.btn_3d.setEnabled(False)
            self.btn_3d.setToolTip(
                "Vue 3D désactivée : Windows bloque le composant VTK. "
                "La vue 2D reste entièrement disponible.")
        groupe = QButtonGroup(self)
        groupe.setExclusive(True)
        groupe.addButton(self.btn_2d)
        groupe.addButton(self.btn_3d)
        self.btn_3d.toggled.connect(self._on_mode_3d)
        barre_mode = QHBoxLayout()
        barre_mode.addWidget(self.btn_2d)
        barre_mode.addWidget(self.btn_3d)
        barre_mode.addStretch(1)
        self.btn_export_image = QPushButton("Exporter l'image")
        self.btn_export_image.setToolTip(
            "Crée un PNG 1080p, 1440p ou 4K avec unités et colorbar.")
        self.btn_export_animation = QPushButton("Exporter l'animation")
        self.btn_export_animation.setToolTip(
            "Crée un GIF ou MP4 horodaté à partir du résultat temporel.")
        self.btn_export_animation.setEnabled(False)
        barre_mode.addWidget(self.btn_export_image)
        barre_mode.addWidget(self.btn_export_animation)


        self._minuteur = QTimer(self)
        self._minuteur.timeout.connect(self._pas_suivant)
        self.btn_debut = QPushButton("|<")
        self.btn_debut.setFixedWidth(32)
        self.btn_debut.clicked.connect(lambda: self.slider_temps.setValue(0))
        self.btn_lecture = QPushButton("Lecture")
        self.btn_lecture.setCheckable(True)
        self.btn_lecture.toggled.connect(self._bascule_lecture)
        self.slider_temps = QSlider(Qt.Orientation.Horizontal)
        self.slider_temps.valueChanged.connect(self._afficher_instant)
        self.label_temps = QLabel("t = 0 s")
        self.label_temps.setMinimumWidth(210)
        self.cb_vitesse = QComboBox()
        for vitesse in _VITESSES_LECTURE:
            self.cb_vitesse.addItem(f"×{vitesse}", vitesse)
        self.cb_vitesse.setCurrentIndex(self.cb_vitesse.findData(1))
        self.cb_vitesse.currentIndexChanged.connect(
            self._vitesse_lecture_changee)
        self.lecteur = QWidget()
        ll = QHBoxLayout(self.lecteur)
        ll.setContentsMargins(0, 4, 0, 4)
        ll.addWidget(self.btn_debut)
        ll.addWidget(self.btn_lecture)
        ll.addWidget(self.slider_temps, stretch=1)
        ll.addWidget(self.label_temps)
        ll.addWidget(QLabel("Vitesse"))
        ll.addWidget(self.cb_vitesse)
        self.lecteur.hide()


        self.figure = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.barre_calques_2d = QWidget()
        barre_calques_2d = QHBoxLayout(self.barre_calques_2d)
        barre_calques_2d.setContentsMargins(0, 2, 0, 2)
        barre_calques_2d.addWidget(QLabel("Calques :"))
        self._boutons_calques_2d = {}
        for cle, texte in (("carte", "Carte"), ("iso", "Iso-valeurs"),
                           ("lignes", "Lignes de champ"),
                           ("fleches", "Flèches")):
            bouton = QPushButton(texte)
            bouton.setCheckable(True)
            bouton.toggled.connect(
                lambda actif, nom=cle: self._basculer_calque_2d(nom, actif))
            barre_calques_2d.addWidget(bouton)
            self._boutons_calques_2d[cle] = bouton
        self.btn_sonde_2d = QPushButton("Sonde")
        self.btn_sonde_2d.setCheckable(True)
        self.btn_sonde_2d.setToolTip(
            "Cliquez pour épingler jusqu'à cinq valeurs sur la carte.")
        self.btn_sonde_2d.toggled.connect(self._basculer_sonde_2d)
        barre_calques_2d.addWidget(self.btn_sonde_2d)
        self.btn_profil_2d = QPushButton("Profil 1D")
        self.btn_profil_2d.setCheckable(True)
        self.btn_profil_2d.setToolTip(
            "Cliquez deux extrémités pour tracer la grandeur le long d'une ligne.")
        self.btn_profil_2d.toggled.connect(self._basculer_profil_2d)
        barre_calques_2d.addWidget(self.btn_profil_2d)
        barre_calques_2d.addStretch(1)
        for cle, bouton in self._boutons_calques_2d.items():
            bouton.setChecked(self._calques_2d[cle])
        page_2d = QWidget()
        l2d = QVBoxLayout(page_2d)
        l2d.setContentsMargins(0, 0, 0, 0)
        l2d.addWidget(self.barre_calques_2d)
        l2d.addWidget(self.canvas, stretch=1)
        l2d.addWidget(self.toolbar)

        self.figure_profil_2d = Figure(figsize=(6, 1.5), dpi=100)
        self.ax_profil_2d = self.figure_profil_2d.add_subplot(111)
        self.canvas_profil_2d = FigureCanvasQTAgg(self.figure_profil_2d)
        self.canvas_profil_2d.setMaximumHeight(180)
        self.profil_2d = QWidget()
        lp2 = QVBoxLayout(self.profil_2d)
        lp2.setContentsMargins(0, 2, 0, 2)
        barre_profil = QHBoxLayout()
        barre_profil.addWidget(QLabel("Profil le long de la ligne"))
        barre_profil.addStretch(1)
        btn_csv_profil = QPushButton("Exporter CSV")
        btn_csv_profil.clicked.connect(self._exporter_profil_2d_csv)
        btn_png_profil = QPushButton("Exporter PNG")
        btn_png_profil.clicked.connect(self._exporter_profil_2d_png)
        barre_profil.addWidget(btn_csv_profil)
        barre_profil.addWidget(btn_png_profil)
        lp2.addLayout(barre_profil)
        lp2.addWidget(self.canvas_profil_2d)
        self.profil_2d.hide()


        self.interactor = QtInteractor(self)




        self._opacite_3d = 1.0
        self._aretes_3d = False
        self._grille_3d = True
        self.barre_3d = QWidget()
        b3 = QHBoxLayout(self.barre_3d)
        b3.setContentsMargins(0, 2, 0, 2)
        for texte, slot in (("Iso", lambda: self._vue_camera("iso")),
                             ("Face", lambda: self._vue_camera("face")),
                             ("Dessus", lambda: self._vue_camera("dessus")),
                             ("Recentrer", lambda: self.interactor.reset_camera())):
            btn = QPushButton(texte)
            btn.setFixedWidth(72)
            btn.clicked.connect(slot)
            b3.addWidget(btn)
        b3.addSpacing(12)
        b3.addWidget(QLabel("Opacité"))
        self.slider_opacite = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacite.setRange(10, 100)
        self.slider_opacite.setValue(100)
        self.slider_opacite.setFixedWidth(90)
        self.slider_opacite.valueChanged.connect(self._changer_opacite)
        b3.addWidget(self.slider_opacite)
        self.btn_aretes = QPushButton("Arêtes")
        self.btn_aretes.setCheckable(True)
        self.btn_aretes.toggled.connect(self._changer_aretes)
        b3.addWidget(self.btn_aretes)
        self.btn_grille = QPushButton("Grille")
        self.btn_grille.setCheckable(True)
        self.btn_grille.setChecked(True)
        self.btn_grille.toggled.connect(self._changer_grille)
        b3.addWidget(self.btn_grille)
        self.btn_fond = QPushButton("Fond sombre")
        self.btn_fond.setCheckable(True)
        self.btn_fond.toggled.connect(self._changer_fond)
        b3.addWidget(self.btn_fond)
        b3.addStretch(1)
        self.barre_3d.hide()




        self.barre_calques_3d = QWidget()
        lcq = QHBoxLayout(self.barre_calques_3d)
        lcq.setContentsMargins(0, 2, 0, 2)
        lcq.addWidget(QLabel("Calques :"))
        self._boutons_calques = {}
        for attr, texte, info in (
                ("carte_scalaire", "Carte",
                 "Surface colorée par la grandeur affichée"),
                ("iso_surfaces", "Iso-surfaces",
                 "Surfaces d'égale valeur de la grandeur affichée"),
                ("lignes_champ", "Lignes de champ",
                 "Lignes de champ ensemencées dans tout le volume"),
                ("fleches", "Flèches", "Vecteurs du champ (glyphes)"),
                ("maillage", "Maillage",
                 "Arêtes du maillage tétraédrique"),
                ("objets_scene", "Objets",
                 "Objets, électrodes et circuits de la scène"),
                ("coupe", "Coupe",
                 "Plan de coupe fini, borné au domaine (réglages dans la "
                 "barre dédiée)"),
        ):
            btn = QPushButton(texte)
            btn.setCheckable(True)
            btn.setToolTip(info)
            btn.toggled.connect(
                lambda actif, a=attr: self._basculer_calque_3d(a, actif))
            lcq.addWidget(btn)
            self._boutons_calques[attr] = btn
        lcq.addStretch(1)
        self.barre_calques_3d.hide()


        self.btn_coupe_3d = self._boutons_calques["coupe"]



        self.barre_coupe_3d = QWidget()
        bc = QHBoxLayout(self.barre_coupe_3d)
        bc.setContentsMargins(0, 2, 0, 2)
        bc.addWidget(QLabel("Coupe — Normale"))
        self.cb_normale_coupe_3d = QComboBox()
        self.cb_normale_coupe_3d.addItems(["X", "Y", "Z", "Oblique"])
        self.cb_normale_coupe_3d.currentTextChanged.connect(
            self._changer_normale_coupe_3d)
        bc.addWidget(self.cb_normale_coupe_3d)
        bc.addWidget(QLabel("Position"))
        self.slider_coupe_3d = QSlider(Qt.Orientation.Horizontal)
        self.slider_coupe_3d.setRange(0, 100)
        self.slider_coupe_3d.setValue(50)
        self.slider_coupe_3d.setFixedWidth(110)
        self.slider_coupe_3d.valueChanged.connect(
            self._changer_position_coupe_3d)
        bc.addWidget(self.slider_coupe_3d)
        bc.addWidget(QLabel("Plans"))
        self.spin_plans_coupe_3d = QSpinBox()
        self.spin_plans_coupe_3d.setRange(1, 3)
        self.spin_plans_coupe_3d.setValue(1)
        self.spin_plans_coupe_3d.valueChanged.connect(
            self._changer_nombre_plans_3d)
        bc.addWidget(self.spin_plans_coupe_3d)
        self.btn_isolignes_coupe_3d = QPushButton("Iso-lignes")
        self.btn_isolignes_coupe_3d.setCheckable(True)
        self.btn_isolignes_coupe_3d.setChecked(True)
        self.btn_isolignes_coupe_3d.toggled.connect(
            self._basculer_isolignes_coupe_3d)
        bc.addWidget(self.btn_isolignes_coupe_3d)
        self.btn_vecteurs_coupe_3d = QPushButton("Vecteurs plan")
        self.btn_vecteurs_coupe_3d.setCheckable(True)
        self.btn_vecteurs_coupe_3d.toggled.connect(
            self._basculer_vecteurs_coupe_3d)
        bc.addWidget(self.btn_vecteurs_coupe_3d)
        self.btn_lignes_coupe_3d = QPushButton("Lignes plan")
        self.btn_lignes_coupe_3d.setCheckable(True)
        self.btn_lignes_coupe_3d.setToolTip(
            "Vraies lignes de champ tangentes au plan de coupe")
        self.btn_lignes_coupe_3d.toggled.connect(
            self._basculer_lignes_coupe_3d)
        bc.addWidget(self.btn_lignes_coupe_3d)
        self.btn_manipuler_coupe_3d = QPushButton("Manipuler le plan")
        self.btn_manipuler_coupe_3d.setCheckable(True)
        self.btn_manipuler_coupe_3d.setToolTip(
            "Afficher un plan manipulable à la souris dans la vue "
            "(poignées compactes). Sinon, la coupe est un maillage fini "
            "strictement borné au domaine, piloté par Normale/Position.")
        self.btn_manipuler_coupe_3d.toggled.connect(
            self._basculer_manipulation_coupe_3d)
        bc.addWidget(self.btn_manipuler_coupe_3d)
        self.btn_clip_boite_3d = QPushButton("Clip boîte")
        self.btn_clip_boite_3d.setCheckable(True)
        self.btn_clip_boite_3d.toggled.connect(
            self._basculer_clip_boite_3d)
        bc.addWidget(self.btn_clip_boite_3d)
        bc.addStretch(1)
        self.barre_coupe_3d.hide()
        self._maj_controles_coupe_3d()




        self.barre_p3_3d = QWidget()
        p3 = QGridLayout(self.barre_p3_3d)
        p3.setContentsMargins(0, 2, 0, 2)
        lab_iso = QLabel("Iso-surfaces")
        self.spin_iso_3d = QSpinBox()
        self.spin_iso_3d.setRange(1, 30)
        self.spin_iso_3d.setValue(8)
        self.spin_iso_3d.valueChanged.connect(self._changer_iso_3d)
        p3.addWidget(lab_iso, 0, 2)
        p3.addWidget(self.spin_iso_3d, 0, 3)
        lab_plage_iso = QLabel("Plage iso min/max")
        self.slider_iso_min_3d = QSlider(Qt.Orientation.Horizontal)
        self.slider_iso_min_3d.setRange(0, 95)
        self.slider_iso_min_3d.setValue(5)
        self.slider_iso_min_3d.setFixedWidth(75)
        self.slider_iso_max_3d = QSlider(Qt.Orientation.Horizontal)
        self.slider_iso_max_3d.setRange(5, 100)
        self.slider_iso_max_3d.setValue(95)
        self.slider_iso_max_3d.setFixedWidth(75)
        self.slider_iso_min_3d.valueChanged.connect(
            self._changer_plage_iso_min_3d)
        self.slider_iso_max_3d.valueChanged.connect(
            self._changer_plage_iso_max_3d)
        p3.addWidget(lab_plage_iso, 0, 4)
        p3.addWidget(self.slider_iso_min_3d, 0, 5)
        p3.addWidget(self.slider_iso_max_3d, 0, 6)

        lab_source = QLabel("Source lignes")
        self.slider_source_lignes_3d = QSlider(Qt.Orientation.Horizontal)
        self.slider_source_lignes_3d.setRange(10, 100)
        self.slider_source_lignes_3d.setValue(55)
        self.slider_source_lignes_3d.setFixedWidth(85)
        self.slider_source_lignes_3d.valueChanged.connect(
            self._changer_source_lignes_3d)
        self.spin_densite_lignes_3d = QSpinBox()
        self.spin_densite_lignes_3d.setRange(2, 15)
        self.spin_densite_lignes_3d.setValue(7)
        self.spin_densite_lignes_3d.valueChanged.connect(
            self._changer_densite_lignes_3d)
        p3.addWidget(lab_source, 1, 0)
        p3.addWidget(self.slider_source_lignes_3d, 1, 1)
        lab_densite = QLabel("Densité")
        p3.addWidget(lab_densite, 1, 2)
        p3.addWidget(self.spin_densite_lignes_3d, 1, 3)

        lab_tubes = QLabel("Tubes")
        self.slider_tubes_3d = QSlider(Qt.Orientation.Horizontal)
        self.slider_tubes_3d.setRange(1, 15)
        self.slider_tubes_3d.setValue(4)
        self.slider_tubes_3d.setFixedWidth(75)
        self.slider_tubes_3d.valueChanged.connect(self._changer_tubes_3d)
        p3.addWidget(lab_tubes, 1, 4)
        p3.addWidget(self.slider_tubes_3d, 1, 5)

        self.spin_pas_glyphes_3d = QSpinBox()
        self.spin_pas_glyphes_3d.setRange(1, 20)
        self.spin_pas_glyphes_3d.setValue(4)
        self.spin_pas_glyphes_3d.valueChanged.connect(
            self._changer_glyphes_3d)
        self.slider_taille_glyphes_3d = QSlider(Qt.Orientation.Horizontal)
        self.slider_taille_glyphes_3d.setRange(3, 25)
        self.slider_taille_glyphes_3d.setValue(12)
        self.slider_taille_glyphes_3d.setFixedWidth(75)
        self.slider_taille_glyphes_3d.valueChanged.connect(
            self._changer_glyphes_3d)
        lab_glyphes = QLabel("Flèches pas/taille")
        p3.addWidget(lab_glyphes, 1, 6)
        p3.addWidget(self.spin_pas_glyphes_3d, 1, 7)
        p3.addWidget(self.slider_taille_glyphes_3d, 1, 8)



        lab_graines = QLabel("Graines")
        self.cb_graines_3d = QComboBox()
        self.cb_graines_3d.addItems(list(MODES_GRAINES))
        self.cb_graines_3d.setToolTip(
            "Répartition des graines des lignes de champ : Volume "
            "(tout l'espace, défaut), Plan, Surface ou Ligne")
        self.cb_graines_3d.currentIndexChanged.connect(
            lambda: self._changer_mode_graines_3d(
                self.cb_graines_3d.currentText()))
        p3.addWidget(lab_graines, 2, 0)
        p3.addWidget(self.cb_graines_3d, 2, 1)
        self.btn_graines_diag_3d = QPushButton("Voir graines")
        self.btn_graines_diag_3d.setCheckable(True)
        self.btn_graines_diag_3d.setToolTip(
            "Diagnostic : afficher les points d'ensemencement")
        self.btn_graines_diag_3d.toggled.connect(
            self._basculer_graines_diag_3d)
        p3.addWidget(self.btn_graines_diag_3d, 2, 2)

        self.btn_sonde_ligne_3d = QPushButton("Sonde-ligne")
        self.btn_sonde_ligne_3d.setCheckable(True)
        self.btn_sonde_ligne_3d.toggled.connect(
            self._basculer_sonde_ligne_3d)
        p3.addWidget(self.btn_sonde_ligne_3d, 0, 8)
        self._controles_volume_p3 = ()
        self._controles_iso_p3 = (
            lab_iso, self.spin_iso_3d, lab_plage_iso,
            self.slider_iso_min_3d, self.slider_iso_max_3d)
        self._controles_lignes_p3 = (
            lab_source, self.slider_source_lignes_3d, lab_densite,
            self.spin_densite_lignes_3d, lab_tubes, self.slider_tubes_3d,
            lab_graines, self.cb_graines_3d, self.btn_graines_diag_3d)
        self._controles_glyphes_p3 = (
            lab_glyphes, self.spin_pas_glyphes_3d,
            self.slider_taille_glyphes_3d)
        self.barre_p3_3d.hide()

        self.stack = QStackedWidget()
        self.stack.addWidget(page_2d)
        self.stack.addWidget(self.interactor)



        self.figure_profil_3d = Figure(figsize=(6, 1.5), dpi=100)
        self.ax_profil_3d = self.figure_profil_3d.add_subplot(111)
        self.canvas_profil_3d = FigureCanvasQTAgg(self.figure_profil_3d)
        self.canvas_profil_3d.setMaximumHeight(180)
        self.profil_3d = QWidget()
        lp = QVBoxLayout(self.profil_3d)
        lp.setContentsMargins(0, 2, 0, 2)
        lp.addWidget(self.canvas_profil_3d)
        self.profil_3d.hide()



        self.label_sonde = QLabel("Sonde : cliquez sur le volume pour lire une valeur.")
        self.label_sonde.setStyleSheet("color: gray;")
        self.label_sonde.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(barre_mode)
        layout.addWidget(self.barre_3d)
        layout.addWidget(self.barre_calques_3d)
        layout.addWidget(self.barre_coupe_3d)
        layout.addWidget(self.barre_p3_3d)
        layout.addWidget(self.lecteur)
        layout.addWidget(self.stack, stretch=1)
        layout.addWidget(self.profil_2d)
        layout.addWidget(self.profil_3d)
        layout.addWidget(self.label_sonde)

        self._synchroniser_boutons_calques()
        self._maj_controles_p3()
        self._accueil()


    def _vue_camera(self, quelle):
        if quelle == "iso":
            self.interactor.view_isometric()
        elif quelle == "face":
            self.interactor.view_xz()
        elif quelle == "dessus":
            self.interactor.view_xy()

    def _redessiner_3d_courant(self):
        if self._dernier_resultat is not None and self.btn_3d.isChecked():
            self._redraw_3d(self._dernier_resultat, self._dernier_kind)

    def _changer_opacite(self, valeur):
        self._opacite_3d = valeur / 100.0
        self._redessiner_3d_courant()

    def _changer_aretes(self, actif):
        self._aretes_3d = bool(actif)
        self._redessiner_3d_courant()

    def _changer_grille(self, actif):
        self._grille_3d = bool(actif)
        self._redessiner_3d_courant()

    def _changer_fond(self, sombre):
        couleurs = theme_app.couleurs(sombre)
        self.interactor.set_background(couleurs["fond_vtk"])


    def appliquer_theme(self, sombre):
        self._theme_sombre = bool(sombre)
        self.btn_fond.blockSignals(True)
        self.btn_fond.setChecked(bool(sombre))
        self.btn_fond.blockSignals(False)
        self._changer_fond(sombre)
        couleurs = theme_app.couleurs(sombre)
        self.label_sonde.setStyleSheet(
            f"color: {couleurs['texte_secondaire']};")
        for figure, canvas in ((self.figure, self.canvas),
                               (self.figure_profil_3d,
                                self.canvas_profil_3d)):
            self._styler_figure(figure)
            canvas.draw_idle()
        if self._dernier_resultat is not None:
            if self.btn_3d.isChecked():
                self._redraw_3d(self._dernier_resultat, self._dernier_kind)
            else:
                self._redraw_2d(self._dernier_resultat, self._dernier_kind)
        elif self._apercu_2d_courant is not None \
                and not self.btn_3d.isChecked():
            champ, titre = self._apercu_2d_courant
            self.afficher_scene_2d(champ, titre)
        elif not self.btn_3d.isChecked():
            self.figure.clf()
            self.ax = self.figure.add_subplot(111)
            self._accueil()

    def _styler_figure(self, figure):
        couleurs = theme_app.couleurs(self._theme_sombre)
        figure.set_facecolor(couleurs["fond"])
        for ax in figure.axes:
            ax.set_facecolor(couleurs["panneau"])
            for spine in ax.spines.values():
                spine.set_color(couleurs["texte_secondaire"])
            ax.tick_params(colors=couleurs["texte_secondaire"],
                           labelcolor=couleurs["texte"])
            ax.xaxis.label.set_color(couleurs["texte"])
            ax.yaxis.label.set_color(couleurs["texte"])
            ax.title.set_color(couleurs["texte"])
            legende = ax.get_legend()
            if legende is not None:
                legende.get_frame().set_facecolor(couleurs["panneau"])
                legende.get_frame().set_edgecolor(couleurs["bordure"])
                for texte in legende.get_texts():
                    texte.set_color(couleurs["texte"])


    def _basculer_calque_2d(self, nom, actif):
        self._calques_2d[nom] = bool(actif)
        if self._dernier_resultat is not None and not self.btn_3d.isChecked():
            self._redraw_2d(self._dernier_resultat, self._dernier_kind)

    def _appliquer_prereglage_calques_2d(self, kind):
        prereglages = {
            "Carte scalaire": ({"carte": True}, False),
            "Iso-valeurs": ({"iso": True}, False),
            "Champ (flèches)": ({"fleches": True}, False),
            "Lignes de champ": ({"carte": True, "lignes": True}, False),
            "Intensité du champ": ({"carte": True}, True),
        }
        reglages, intensite = prereglages.get(
            kind, prereglages["Carte scalaire"])
        for nom in self._calques_2d:
            self._calques_2d[nom] = bool(reglages.get(nom, False))
        self._fond_intensite_2d = intensite
        for nom, bouton in self._boutons_calques_2d.items():
            bouton.blockSignals(True)
            bouton.setChecked(self._calques_2d[nom])
            bouton.blockSignals(False)

    def _basculer_calque_3d(self, attr, actif):
        setattr(self._calques_3d, attr, bool(actif))
        if attr == "coupe":
            self._options_coupe_3d.active = bool(actif)
            if actif and not self._options_coupe_3d.plans \
                    and self._champ_3d_courant is not None:
                self._reconstruire_plans_coupe_3d()
            self._maj_controles_coupe_3d()
        self._maj_controles_p3()
        self._maj_barres_3d()
        self._redessiner_3d_courant()

    def _synchroniser_boutons_calques(self):
        for attr, btn in self._boutons_calques.items():
            btn.blockSignals(True)
            btn.setChecked(bool(getattr(self._calques_3d, attr)))
            btn.blockSignals(False)

    def _appliquer_prereglage_calques(self, kind):
        prereglage = fem3d_render.calques_depuis_mode(
            kind or "Carte scalaire")
        c = self._calques_3d
        c.carte_scalaire = prereglage.carte_scalaire
        c.volume = prereglage.volume
        c.iso_surfaces = prereglage.iso_surfaces
        c.lignes_champ = prereglage.lignes_champ
        c.fleches = prereglage.fleches
        self._synchroniser_boutons_calques()
        self._maj_controles_p3()
        self._maj_barres_3d()

    def _maj_barres_3d(self):
        en3d = self.btn_3d.isChecked()
        c = self._calques_3d
        self.barre_3d.setVisible(en3d)
        self.barre_calques_3d.setVisible(en3d)
        self.barre_coupe_3d.setVisible(en3d and c.coupe)
        self.barre_p3_3d.setVisible(en3d and (
            c.volume or c.iso_surfaces or c.lignes_champ or c.fleches))


    def configurer_defaut_magnetique_3d(self, selectionner_intensite=True):
        if selectionner_intensite:
            self._selection_scalaire_3d = "Intensité du champ"
        self._options_coupe_3d.active = True
        self._calques_3d.coupe = True
        self._synchroniser_boutons_calques()
        self._maj_controles_coupe_3d()
        self._maj_barres_3d()

    def _maj_controles_p3(self):
        c = self._calques_3d
        for widget in self._controles_volume_p3:
            widget.setVisible(c.volume)
        for widget in self._controles_iso_p3:
            widget.setVisible(c.iso_surfaces)
        for widget in self._controles_lignes_p3:
            widget.setVisible(c.lignes_champ)
        for widget in self._controles_glyphes_p3:
            widget.setVisible(c.fleches)

    def _changer_iso_3d(self, nombre):
        self._options_rendu_3d.nombre_isosurfaces = int(nombre)
        self._redessiner_3d_courant()

    def _changer_plage_iso_min_3d(self, valeur):
        if valeur >= self.slider_iso_max_3d.value():
            self.slider_iso_max_3d.setValue(min(100, valeur + 1))
        self._options_rendu_3d.fraction_iso_min = valeur / 100.0
        self._options_rendu_3d.fraction_iso_max = (
            self.slider_iso_max_3d.value() / 100.0)
        self._redessiner_3d_courant()

    def _changer_plage_iso_max_3d(self, valeur):
        if valeur <= self.slider_iso_min_3d.value():
            self.slider_iso_min_3d.setValue(max(0, valeur - 1))
        self._options_rendu_3d.fraction_iso_min = (
            self.slider_iso_min_3d.value() / 100.0)
        self._options_rendu_3d.fraction_iso_max = valeur / 100.0
        self._redessiner_3d_courant()

    def _changer_source_lignes_3d(self, valeur):
        self._options_rendu_3d.taille_source_lignes = valeur / 100.0
        self._redessiner_3d_courant()

    def _changer_densite_lignes_3d(self, valeur):
        self._options_rendu_3d.densite_lignes = int(valeur)
        self._redessiner_3d_courant()

    def _changer_tubes_3d(self, valeur):
        self._options_rendu_3d.rayon_tubes = valeur / 1000.0
        self._redessiner_3d_courant()

    def _changer_glyphes_3d(self, _valeur):
        self._options_rendu_3d.pas_glyphes = self.spin_pas_glyphes_3d.value()
        self._options_rendu_3d.taille_glyphes = (
            self.slider_taille_glyphes_3d.value() / 100.0)
        self._redessiner_3d_courant()

    def _basculer_sonde_ligne_3d(self, actif):
        if not actif:
            self.profil_3d.hide()
        self._redessiner_3d_courant()


    def set_scalaire_3d(self, selection):
        if selection in fem3d_render.SCALAIRES_3D:
            self._selection_scalaire_3d = selection

    def _libelle_kappa_3d(self):
        return {
            "Electrostatique": "Permittivité relative εr",
            "Thermique": "Conductivité thermique κ (W/m.K)",
            "Magnetostatique": "Coefficient magnétique 1/μr",
        }.get(self.domaine.nom, "Coefficient matériau κ")

    def _appliquer_defauts_superpositions_coupe(self, kind):
        isolignes, vecteurs, lignes = superpositions_coupe_par_defaut(kind)
        self._options_coupe_3d.isolignes = isolignes
        self._options_coupe_3d.vecteurs_projetes = vecteurs
        self._options_coupe_3d.lignes_champ = lignes
        for bouton, valeur in ((self.btn_isolignes_coupe_3d, isolignes),
                               (self.btn_vecteurs_coupe_3d, vecteurs),
                               (self.btn_lignes_coupe_3d, lignes)):
            bouton.blockSignals(True)
            bouton.setChecked(valeur)
            bouton.blockSignals(False)

    def _maj_controles_coupe_3d(self):
        actif = self._calques_3d.coupe
        for widget in (
                self.cb_normale_coupe_3d, self.slider_coupe_3d,
                self.spin_plans_coupe_3d, self.btn_isolignes_coupe_3d,
                self.btn_vecteurs_coupe_3d, self.btn_lignes_coupe_3d,
                self.btn_manipuler_coupe_3d):
            widget.setEnabled(actif)

    def _reconstruire_plans_coupe_3d(self, preserver_normales=False):
        champ = self._champ_3d_courant
        if champ is None:
            return
        minimum = champ.mesh.p.min(axis=1)
        maximum = champ.mesh.p.max(axis=1)
        bornes = (minimum[0], maximum[0], minimum[1], maximum[1],
                  minimum[2], maximum[2])
        normale_base = {
            "X": (1.0, 0.0, 0.0),
            "Y": (0.0, 1.0, 0.0),
            "Z": (0.0, 0.0, 1.0),
            "Oblique": (1.0, 1.0, 1.0),
        }[self.cb_normale_coupe_3d.currentText()]
        n_plans = self.spin_plans_coupe_3d.value()
        position = self.slider_coupe_3d.value() / 100.0
        fractions = fractions_plans(position, n_plans)
        anciens = list(self._options_coupe_3d.plans)
        plans = []
        for i, fraction in enumerate(fractions):
            normale = (anciens[i].normale
                        if preserver_normales and i < len(anciens)
                        else normale_base)
            origine = origine_plan_dans_bornes(
                bornes, normale, fraction)
            plans.append(fem3d_render.PlanCoupe3D(
                normale=tuple(normale), origine=origine))
        self._options_coupe_3d.plans = plans
        self._options_coupe_3d.orientation_libre = (
            self.cb_normale_coupe_3d.currentText() == "Oblique")
        self._bornes_plans_3d = tuple(float(v) for v in bornes)

    def _assurer_plans_coupe_3d(self, champ):
        minimum = champ.mesh.p.min(axis=1)
        maximum = champ.mesh.p.max(axis=1)
        bornes = (minimum[0], maximum[0], minimum[1], maximum[1],
                  minimum[2], maximum[2])
        if (self._bornes_plans_3d is None
                or not np.allclose(self._bornes_plans_3d, bornes)
                or len(self._options_coupe_3d.plans)
                != self.spin_plans_coupe_3d.value()):
            self._reconstruire_plans_coupe_3d(
                preserver_normales=(
                    self.cb_normale_coupe_3d.currentText() == "Oblique"))

    def _changer_normale_coupe_3d(self, _texte):
        self._reconstruire_plans_coupe_3d(preserver_normales=False)
        self._redessiner_3d_courant()

    def _changer_position_coupe_3d(self, _valeur):
        self._reconstruire_plans_coupe_3d(
            preserver_normales=(
                self.cb_normale_coupe_3d.currentText() == "Oblique"))
        self._redessiner_3d_courant()

    def _changer_nombre_plans_3d(self, _valeur):
        self._reconstruire_plans_coupe_3d(
            preserver_normales=(
                self.cb_normale_coupe_3d.currentText() == "Oblique"))
        self._redessiner_3d_courant()

    def _basculer_isolignes_coupe_3d(self, actif):
        self._options_coupe_3d.isolignes = bool(actif)
        self._redessiner_3d_courant()

    def _basculer_vecteurs_coupe_3d(self, actif):
        self._options_coupe_3d.vecteurs_projetes = bool(actif)
        self._redessiner_3d_courant()

    def _basculer_lignes_coupe_3d(self, actif):
        self._options_coupe_3d.lignes_champ = bool(actif)
        self._redessiner_3d_courant()

    def _basculer_manipulation_coupe_3d(self, actif):
        self._options_coupe_3d.manipuler_widget = bool(actif)
        self._redessiner_3d_courant()

    def _changer_mode_graines_3d(self, mode):
        self._options_rendu_3d.graines.mode = mode
        self._redessiner_3d_courant()

    def _basculer_graines_diag_3d(self, actif):
        self._options_rendu_3d.graines.afficher_graines = bool(actif)
        self._redessiner_3d_courant()

    def _basculer_clip_boite_3d(self, actif):
        self._options_coupe_3d.clip_boite = bool(actif)
        self._redessiner_3d_courant()

    def _est_3d_natif(self, result):
        if hasattr(result, "champs"):
            champ = result.champs[0] if result.champs else None
        else:
            champ = getattr(result, "champ", result)
        return isinstance(champ, Field3D)

    def redraw(self, result, kind):
        if result is None:
            return
        self._apercu_2d_courant = None
        self._desactiver_selection_scene()
        if kind != self._dernier_kind:
            self._appliquer_defauts_superpositions_coupe(kind)
            self._appliquer_prereglage_calques(kind)
            self._appliquer_prereglage_calques_2d(kind)
        self._dernier_kind = kind
        if hasattr(result, "champs"):
            if result is not self._transitoire:
                self._activer_lecteur(result)
            else:
                self._afficher_instant(self.slider_temps.value())
        else:
            self._desactiver_lecteur()
            self._dernier_resultat = result
            self._forcer_3d_si_natif(result)
            if self.btn_3d.isChecked():
                self._redraw_3d(result, kind)
            else:
                self._redraw_2d(result, kind)

    def _forcer_3d_si_natif(self, result):
        natif_3d = self._est_3d_natif(result)
        self.btn_2d.setEnabled(not natif_3d)
        if natif_3d and not self.btn_3d.isChecked():
            self.btn_3d.blockSignals(True)
            self.btn_3d.setChecked(True)
            self.btn_3d.blockSignals(False)
            self.stack.setCurrentIndex(1)
            self._maj_barres_3d()

    def _redraw_2d(self, result, kind):
        if self._est_3d_natif(result):
            return
        dom = self.domaine
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        viz.dessiner_calques(
            self.ax, result.champ, self._calques_2d,
            dom.champ_fn, dom.scalaire, dom.champ,
            fond_intensite=self._fond_intensite_2d)
        self._dessiner_mesures_2d(result.champ)
        self._styler_figure(self.figure)
        self.figure.tight_layout()
        self.canvas.draw()
        self._actualiser_profil_2d(result.champ)

    def _redraw_3d(self, result, kind):
        self._maj_controles_p3()
        if self._est_3d_natif(result):
            self._champ_3d_courant = result.champ
            self._assurer_plans_coupe_3d(result.champ)
            self._maj_barres_3d()
            self.barre_coupe_3d.setEnabled(True)
            self.barre_p3_3d.setEnabled(True)
            libelle = (getattr(result.champ, "libelle_scalaire", None)
                       or self.domaine.scalaire)



            conserver = self._scalaire_sonde_3d is not None
            self._scalaire_sonde_3d = fem3d_render.dessiner(
                self.interactor, result.champ, kind,
                scalaire=libelle,
                opacite=self._opacite_3d,
                aretes=self._aretes_3d,
                grille_axes=self._grille_3d,
                libelle_champ=self.domaine.champ,
                kappa_pondere=(self.domaine.nom == "Thermique"),
                selection_scalaire=self._selection_scalaire_3d,
                libelle_kappa=self._libelle_kappa_3d(),
                options_coupe=self._options_coupe_3d,
                options_rendu=self._options_rendu_3d,
                calques=self._calques_3d,
                conserver_camera=conserver,
                theme_sombre=self._theme_sombre)
            self._activer_sonde()
            self._installer_sonde_ligne_3d()
            return
        dom = self.domaine
        self._desactiver_sonde()
        self.barre_coupe_3d.setEnabled(False)
        self.barre_p3_3d.setEnabled(False)
        viz3d.dessiner(self.interactor, result.champ, kind,
                        dom.champ_fn, dom.scalaire, dom.champ,
                        theme_sombre=self._theme_sombre)


    def _activer_sonde(self):
        self._desactiver_selection_scene()
        self._retirer_observateur_mouvement_3d()
        if self._sonde_activee:
            self.interactor.disable_picking()
        self.interactor.enable_point_picking(
            callback=self._sur_pick_3d, show_message=False,
            left_clicking=True, show_point=True)
        self._sonde_activee = True
        self._installer_observateur_mouvement_3d()
        if self._cb_placement_3d is None:
            self.label_sonde.setText(
                "Sonde : survolez la coupe ou le volume pour lire une valeur.")
        self.label_sonde.show()

    def _desactiver_sonde(self):
        self._retirer_observateur_mouvement_3d()
        if self._sonde_activee:
            self.interactor.disable_picking()
            self._sonde_activee = False
        self._champ_3d_courant = None
        self._scalaire_sonde_3d = None
        self.label_sonde.hide()
        self.profil_3d.hide()

    def _desactiver_selection_scene(self):
        if self._widget_affine_scene is not None:
            try:
                self._widget_affine_scene.remove()
            except (AttributeError, RuntimeError):
                pass
            self._widget_affine_scene = None
        if self._selection_scene_active:
            try:
                self.interactor.disable_picking()
            except (AttributeError, RuntimeError):
                pass
            self._selection_scene_active = False
        self._correspondance_acteurs_scene = {}

    def afficher_scene_3d(self, scene, index_selectionne=None,
                          callback_selection=None, callback_transformation=None,
                          mode_transformation="Déplacer / tourner"):
        self._desactiver_sonde()
        self._desactiver_selection_scene()
        self.btn_3d.blockSignals(True)
        self.btn_3d.setChecked(True)
        self.btn_3d.blockSignals(False)
        self.btn_2d.setEnabled(False)
        self.stack.setCurrentIndex(1)
        self.barre_3d.show()
        self.barre_calques_3d.hide()
        self.barre_coupe_3d.hide()
        self.barre_p3_3d.hide()
        self._correspondance_acteurs_scene = (
            fem3d_render.dessiner_scene_seule(
                self.interactor, scene, index_selectionne,
                theme_sombre=self._theme_sombre))
        self._installer_transformation_scene(
            scene, index_selectionne, callback_transformation,
            mode_transformation)
        if callback_selection is None \
                or not hasattr(self.interactor, "enable_mesh_picking"):
            return

        def _selectionner(acteur):
            index = self._correspondance_acteurs_scene.get(id(acteur))
            if index is not None:
                callback_selection(index)

        self.interactor.enable_mesh_picking(
            callback=_selectionner, use_actor=True, show=False,
            show_message=False, left_clicking=True)
        self._selection_scene_active = True

    def afficher_scene_2d(self, field, titre):
        self._dernier_resultat = None
        self._dernier_kind = None
        self._desactiver_lecteur()
        self._desactiver_sonde()
        self.btn_2d.setEnabled(True)
        self.btn_2d.blockSignals(True)
        self.btn_2d.setChecked(True)
        self.btn_2d.blockSignals(False)
        self.stack.setCurrentIndex(0)
        self._taille_apercu_2d = float(
            getattr(field, "taille_domaine", 1.0) or 1.0)
        self._apercu_2d_courant = (field, titre)
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        viz.plot_apercu_scene(self.ax, field, titre)
        self._styler_figure(self.figure)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _acteur_scene(self, scene, index):
        elements = list(scene.items) + list(scene.circuits)
        if not isinstance(index, int) or not 0 <= index < len(elements):
            return None
        element = elements[index]
        prefixe = ("scene_item_" if index < len(scene.items)
                   else "scene_circuit_")
        renderer = getattr(self.interactor, "renderer", None)
        acteurs = getattr(renderer, "actors", {})
        return acteurs.get(prefixe + element.identifiant) \
            if hasattr(acteurs, "get") else None

    def _installer_transformation_scene(
            self, scene, index, callback, mode):
        if callback is None:
            return
        acteur = self._acteur_scene(scene, index)
        if acteur is None:
            return
        try:
            bornes = tuple(float(v) for v in acteur.bounds)
        except (AttributeError, TypeError, ValueError):
            return

        if mode == "Redimensionner" and hasattr(
                self.interactor, "add_box_widget"):
            def _redimensionner(polydata):
                try:
                    nouvelles = tuple(float(v) for v in polydata.bounds)
                except (AttributeError, TypeError, ValueError):
                    return
                if np.allclose(nouvelles, bornes, rtol=1e-9, atol=1e-12):
                    return
                callback(index, "bounds", nouvelles, bornes)

            try:
                self.interactor.add_box_widget(
                    _redimensionner, bounds=bornes, factor=1.0,
                    rotation_enabled=False, color="#f59e0b",
                    use_planes=False, outline_translation=True,
                    interaction_event="end")
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass
            return

        if not hasattr(self.interactor, "add_affine_transform_widget"):
            return

        def _appliquer(matrice):
            try:
                valeurs = np.asarray(matrice, dtype=float).reshape((4, 4))
            except (TypeError, ValueError):
                return
            callback(index, "affine", valeurs, bornes)

        try:
            self._widget_affine_scene = \
                self.interactor.add_affine_transform_widget(
                    acteur, origin=acteur.center, scale=0.22,
                    line_radius=0.025, always_visible=True,
                    release_callback=_appliquer)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self._widget_affine_scene = None

    def _installer_observateur_mouvement_3d(self):
        iren = getattr(self.interactor, "iren", None)
        if iren is None or self._observer_mouvement_3d is not None:
            return
        try:
            if hasattr(iren, "add_observer"):
                identifiant = iren.add_observer(
                    "MouseMoveEvent", self._sur_mouvement_3d)
                self._observer_mouvement_3d = (iren, identifiant, True)
            else:
                vtk_iren = getattr(iren, "interactor", iren)
                identifiant = vtk_iren.AddObserver(
                    "MouseMoveEvent", self._sur_mouvement_3d)
                self._observer_mouvement_3d = (vtk_iren, identifiant, False)
        except (AttributeError, RuntimeError):

            self._observer_mouvement_3d = None

    def _retirer_observateur_mouvement_3d(self):
        if self._observer_mouvement_3d is None:
            return
        iren, identifiant, enveloppe_pyvista = self._observer_mouvement_3d
        try:
            if enveloppe_pyvista and hasattr(iren, "remove_observer"):
                iren.remove_observer(identifiant)
            else:
                iren.RemoveObserver(identifiant)
        except (AttributeError, RuntimeError):
            pass
        self._observer_mouvement_3d = None

    def _sur_mouvement_3d(self, *_args):
        if self._cb_placement_3d is not None or self._scalaire_sonde_3d is None:
            return
        maintenant = monotonic()
        if maintenant - self._dernier_mouvement_sonde < 0.04:
            return
        self._dernier_mouvement_sonde = maintenant

        iren = getattr(self.interactor, "iren", None)
        if iren is None:
            return
        try:
            if hasattr(iren, "get_event_position"):
                x, y = iren.get_event_position()
            else:
                vtk_iren = getattr(iren, "interactor", iren)
                x, y = vtk_iren.GetEventPosition()
            trouve = self._picker_sonde_3d.Pick(
                int(x), int(y), 0, self.interactor.renderer)
            if trouve:
                self._mettre_a_jour_sonde_3d(
                    self._picker_sonde_3d.GetPickPosition())
        except (AttributeError, RuntimeError, TypeError):
            return

    def _mettre_a_jour_sonde_3d(self, point):
        info = self._scalaire_sonde_3d
        if info is None:
            return
        valeur, p = info.valeur_au_point(point)
        unite = unite_depuis_libelle(info.libelle)
        valeur_formatee = (format_grandeur(valeur, unite)
                           if unite else f"{valeur:.4g}")
        self.label_sonde.setText(
            f"Sonde : {info.libelle} = {valeur_formatee} "
            f"au point ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f}) m.")

    def _installer_sonde_ligne_3d(self):
        info = self._scalaire_sonde_3d
        if not self.btn_sonde_ligne_3d.isChecked() or info is None:
            self.profil_3d.hide()
            return
        if not hasattr(self.interactor, "add_line_widget"):
            return
        bounds = tuple(float(v) for v in info.grille.bounds)
        minimum = np.array([bounds[0], bounds[2], bounds[4]])
        maximum = np.array([bounds[1], bounds[3], bounds[5]])
        if self._extremites_sonde_ligne_3d is None:
            centre = (minimum + maximum) / 2.0
            axe = (2 if self.domaine.nom == "Magnetostatique"
                   else int(np.argmax(maximum - minimum)))
            point_a, point_b = centre.copy(), centre.copy()
            point_a[axe], point_b[axe] = minimum[axe], maximum[axe]
            self._extremites_sonde_ligne_3d = (
                tuple(point_a), tuple(point_b))
        else:
            point_a, point_b = self._extremites_sonde_ligne_3d
            self._extremites_sonde_ligne_3d = (
                tuple(np.clip(point_a, minimum, maximum)),
                tuple(np.clip(point_b, minimum, maximum)))

        def _actualiser_profil(point_a, point_b):
            point_a = tuple(float(v) for v in point_a)
            point_b = tuple(float(v) for v in point_b)
            if np.linalg.norm(np.asarray(point_b) - np.asarray(point_a)) <= 1e-12:
                return
            self._extremites_sonde_ligne_3d = (point_a, point_b)
            try:
                echantillon = info.grille.sample_over_line(
                    point_a, point_b, resolution=200)
                valeurs = np.asarray(
                    echantillon[info.nom_tableau], dtype=float)
                valide = np.ones(len(valeurs), dtype=bool)
                if "vtkValidPointMask" in echantillon.array_names:
                    valide &= np.asarray(
                        echantillon["vtkValidPointMask"], dtype=bool)
                valide &= np.isfinite(valeurs)
                abscisses = abscisses_cumulees(echantillon.points)
                self.ax_profil_3d.clear()
                self.ax_profil_3d.plot(
                    abscisses[valide], valeurs[valide],
                    color="#2563eb", linewidth=1.8)
                self.ax_profil_3d.set_xlabel("Distance le long du segment (m)")
                self.ax_profil_3d.set_ylabel(info.libelle)
                self.ax_profil_3d.grid(True, alpha=0.25)
                self._styler_figure(self.figure_profil_3d)
                self.figure_profil_3d.tight_layout()
                self.canvas_profil_3d.draw_idle()
                self.profil_3d.show()
            except (KeyError, RuntimeError, TypeError, ValueError):
                self.profil_3d.hide()




        point_a, point_b = self._extremites_sonde_ligne_3d
        widget = self.interactor.add_line_widget(
            _actualiser_profil, bounds=bounds, factor=1.0,
            resolution=200, color="#2563eb", use_vertices=True,
            interaction_event="always")
        try:
            widget.SetPoint1(*point_a)
            widget.SetPoint2(*point_b)
        except TypeError:
            widget.SetPoint1(point_a)
            widget.SetPoint2(point_b)
        try:
            widget.InvokeEvent("InteractionEvent")
        except AttributeError:
            _actualiser_profil(point_a, point_b)

    def _sur_pick_3d(self, point):
        if self._cb_placement_3d is not None:
            self._cb_placement_3d(float(point[0]), float(point[1]), float(point[2]))
            return
        self._mettre_a_jour_sonde_3d(point)

    @staticmethod
    def _echantillonner_2d(champ, x, y):
        valeurs = np.asarray(champ.V, dtype=float)
        ny, nx = valeurs.shape
        L = float(getattr(champ, "taille_domaine", 1.0) or 1.0)
        xi = np.clip(np.asarray(x, dtype=float) / L * (nx - 1), 0, nx - 1)
        yi = np.clip(np.asarray(y, dtype=float) / L * (ny - 1), 0, ny - 1)
        x0 = np.floor(xi).astype(int)
        y0 = np.floor(yi).astype(int)
        x1 = np.minimum(x0 + 1, nx - 1)
        y1 = np.minimum(y0 + 1, ny - 1)
        tx, ty = xi - x0, yi - y0
        return ((1 - tx) * (1 - ty) * valeurs[y0, x0]
                + tx * (1 - ty) * valeurs[y0, x1]
                + (1 - tx) * ty * valeurs[y1, x0]
                + tx * ty * valeurs[y1, x1])

    def _mettre_a_jour_connexion_clic_2d(self):
        actif = (self._cb_placement_2d is not None
                 or self.btn_sonde_2d.isChecked()
                 or self.btn_profil_2d.isChecked())
        if actif and self._cid_placement is None:
            self._cid_placement = self.canvas.mpl_connect(
                "button_press_event", self._sur_clic_2d)
        elif not actif and self._cid_placement is not None:
            self.canvas.mpl_disconnect(self._cid_placement)
            self._cid_placement = None

    def _basculer_sonde_2d(self, actif):
        if actif and self.btn_profil_2d.isChecked():
            self.btn_profil_2d.setChecked(False)
        self._mettre_a_jour_connexion_clic_2d()
        if actif:
            self.label_sonde.setText(
                "Sonde 2D : cliquez sur la carte pour épingler une valeur.")
            self.label_sonde.show()

    def _basculer_profil_2d(self, actif):
        if actif:
            if self.btn_sonde_2d.isChecked():
                self.btn_sonde_2d.setChecked(False)
            self._points_profil_2d = []
            self.label_sonde.setText(
                "Profil 1D : cliquez la première puis la seconde extrémité.")
            self.label_sonde.show()
        self._mettre_a_jour_connexion_clic_2d()

    def _dessiner_mesures_2d(self, champ):
        unite = unite_depuis_libelle(self.domaine.scalaire)
        details = []
        for index, (x, y) in enumerate(self._sondes_2d, start=1):
            valeur = float(self._echantillonner_2d(champ, x, y))
            texte = (format_grandeur(valeur, unite)
                     if unite else f"{valeur:.4g}")
            self.ax.plot(x, y, marker="o", color="#22c55e",
                         markeredgecolor="white", markersize=6, zorder=20)
            self.ax.annotate(
                f"S{index}: {texte}", (x, y), xytext=(6, 7),
                textcoords="offset points", fontsize=8, color="white",
                bbox={"boxstyle": "round,pad=0.25", "fc": "#111827",
                      "alpha": 0.82}, zorder=21)
            details.append(f"S{index} ({x:.3g}, {y:.3g}) m : {texte}")
        if len(self._points_profil_2d) == 2:
            (xa, ya), (xb, yb) = self._points_profil_2d
            self.ax.plot([xa, xb], [ya, yb], color="#2563eb",
                         linewidth=2.0, marker="o", zorder=19)
        if details and not self.btn_profil_2d.isChecked():
            self.label_sonde.setText("Sondes — " + " · ".join(details))
            self.label_sonde.show()

    def _actualiser_profil_2d(self, champ=None):
        if len(self._points_profil_2d) != 2:
            return
        champ = champ or getattr(self._dernier_resultat, "champ", None)
        if champ is None or getattr(champ.V, "ndim", 0) != 2:
            return
        point_a, point_b = np.asarray(self._points_profil_2d, dtype=float)
        fraction = np.linspace(0.0, 1.0, 250)
        points = point_a[None, :] + fraction[:, None] * (point_b - point_a)
        valeurs = np.asarray(
            self._echantillonner_2d(champ, points[:, 0], points[:, 1]))
        longueur = float(np.linalg.norm(point_b - point_a))
        distances = fraction * longueur
        self._donnees_profil_2d = (distances, valeurs)
        self.ax_profil_2d.clear()
        self.ax_profil_2d.plot(distances, valeurs, color="#2563eb")
        self.ax_profil_2d.set_xlabel(tr("Distance le long du segment (m)"))
        self.ax_profil_2d.set_ylabel(tr(self.domaine.scalaire))
        self.ax_profil_2d.set_title(
            f"min = {valeurs.min():.4g} · max = {valeurs.max():.4g}",
            fontsize=9)
        self.ax_profil_2d.grid(True, alpha=0.25)
        self._styler_figure(self.figure_profil_2d)
        self.figure_profil_2d.tight_layout()
        self.canvas_profil_2d.draw_idle()
        self.profil_2d.show()

    def _exporter_profil_2d_csv(self):
        if self._donnees_profil_2d is None:
            return
        chemin, _ = QFileDialog.getSaveFileName(
            self, tr("Exporter le profil"), "", "CSV (*.csv)")
        if not chemin:
            return
        import csv
        distances, valeurs = self._donnees_profil_2d
        with open(chemin, "w", encoding="utf-8", newline="") as fichier:
            writer = csv.writer(fichier)
            writer.writerow(["distance_m", self.domaine.scalaire])
            writer.writerows(zip(distances, valeurs))

    def _exporter_profil_2d_png(self):
        if self._donnees_profil_2d is None:
            return
        chemin, _ = QFileDialog.getSaveFileName(
            self, tr("Exporter le profil"), "", "PNG (*.png)")
        if chemin:
            self.figure_profil_2d.savefig(
                chemin, dpi=200, bbox_inches="tight", facecolor="white")


    def activer_placement_2d(self, callback):
        self._cb_placement_2d = callback
        self._mettre_a_jour_connexion_clic_2d()

    def _sur_clic_2d(self, event):
        if event.button != 1:
            return
        if event.xdata is None or event.ydata is None:
            return
        champ = getattr(self._dernier_resultat, "champ", None)
        if champ is not None and getattr(champ.V, "ndim", 0) == 2:
            L = float(getattr(champ, "taille_domaine", 1.0) or 1.0)
            x_m = min(max(float(event.xdata), 0.0), L)
            y_m = min(max(float(event.ydata), 0.0), L)
            if self.btn_profil_2d.isChecked():
                self._points_profil_2d.append((x_m, y_m))
                if len(self._points_profil_2d) == 1:
                    self.label_sonde.setText(
                        "Profil 1D : première extrémité posée; cliquez la seconde.")
                else:
                    self._points_profil_2d = self._points_profil_2d[-2:]
                    self._actualiser_profil_2d(champ)
                    self.btn_profil_2d.setChecked(False)
                    self._redraw_2d(self._dernier_resultat, self._dernier_kind)
                return
            if self.btn_sonde_2d.isChecked():
                self._sondes_2d.append((x_m, y_m))
                self._sondes_2d = self._sondes_2d[-5:]
                self._redraw_2d(self._dernier_resultat, self._dernier_kind)
                return
        if self._cb_placement_2d is None:
            return
        if champ is not None and getattr(champ, "V", None) is not None \
                and getattr(champ.V, "ndim", 0) == 2:
            L = float(getattr(champ, "taille_domaine", 1.0) or 1.0)
            x, y = event.xdata / L, event.ydata / L
        else:
            L = self._taille_apercu_2d or 1.0
            x, y = event.xdata / L, event.ydata / L
        self._cb_placement_2d(min(max(float(x), 0.0), 1.0),
                               min(max(float(y), 0.0), 1.0))

    def activer_placement_3d(self, callback):
        self._cb_placement_3d = callback
        if callback is not None:
            self.label_sonde.setText(
                "Placement : cliquez sur le volume pour poser l'obstacle "
                "(coordonnees du point clique).")
            self.label_sonde.show()
        elif self._sonde_activee:
            self.label_sonde.setText(
                "Sonde : survolez la coupe ou le volume pour lire une valeur.")

    def _on_mode_3d(self, actif):
        self.stack.setCurrentIndex(1 if actif else 0)
        self._maj_barres_3d()
        if actif:
            self.profil_2d.hide()
        else:
            self.profil_3d.hide()
            if self._donnees_profil_2d is not None:
                self.profil_2d.show()
        if self._transitoire is not None:
            self._afficher_instant(self.slider_temps.value())
        elif self._dernier_resultat is not None:
            if actif:
                self._redraw_3d(self._dernier_resultat, self._dernier_kind)
            else:
                self._redraw_2d(self._dernier_resultat, self._dernier_kind)

    def champ_affiche(self):
        return self._dernier_resultat.champ if self._dernier_resultat is not None else None


    def _activer_lecteur(self, transitoire):
        self._minuteur.stop()
        self.btn_lecture.setChecked(False)
        self._transitoire = transitoire
        self.btn_export_animation.setEnabled(True)
        self._forcer_3d_si_natif(transitoire)
        self.lecteur.show()
        self.slider_temps.blockSignals(True)
        self.slider_temps.setRange(0, len(transitoire.champs) - 1)
        self.slider_temps.setValue(len(transitoire.champs) - 1)
        self.slider_temps.blockSignals(False)
        self._afficher_instant(len(transitoire.champs) - 1)

    def _desactiver_lecteur(self):
        if self._transitoire is not None:
            self._minuteur.stop()
            self.btn_lecture.setChecked(False)
            self._transitoire = None
        self.btn_export_animation.setEnabled(False)
        self.lecteur.hide()

    def _afficher_instant(self, index):
        if self._transitoire is None:
            return
        champ = self._transitoire.champs[index]
        t = self._transitoire.instants[index]
        vitesse = int(self.cb_vitesse.currentData() or 1)
        self.label_temps.setText(
            f"t = {format_duree(t)} — lecture ×{vitesse}")
        self._dernier_resultat = _Instant(champ)
        if self.btn_3d.isChecked():
            self._redraw_3d(self._dernier_resultat, self._dernier_kind)
        else:
            self._redraw_2d(self._dernier_resultat, self._dernier_kind)

    def _bascule_lecture(self, actif):
        if actif:
            if self.slider_temps.value() >= self.slider_temps.maximum():
                self.slider_temps.setValue(0)
            self._minuteur.start(self._intervalle_lecture_ms())
            self.btn_lecture.setText("Pause")
        else:
            self._minuteur.stop()
            self.btn_lecture.setText("Lecture")

    def _intervalle_lecture_ms(self):
        if self._transitoire is None or len(self._transitoire.instants) < 2:
            return 100
        index = min(self.slider_temps.value(),
                    len(self._transitoire.instants) - 2)
        delta_simule = max(
            0.001,
            float(self._transitoire.instants[index + 1])
            - float(self._transitoire.instants[index]))
        vitesse = max(1, int(self.cb_vitesse.currentData() or 1))
        return int(max(10, min(2_147_000_000,
                               1000.0 * delta_simule / vitesse)))

    def _vitesse_lecture_changee(self, _index=None):
        if self._transitoire is not None:
            self._afficher_instant(self.slider_temps.value())
        if self.btn_lecture.isChecked():
            self._minuteur.start(self._intervalle_lecture_ms())

    def set_vitesse_lecture(self, vitesse):
        index = self.cb_vitesse.findData(int(vitesse))
        if index >= 0:
            self.cb_vitesse.setCurrentIndex(index)

    def _pas_suivant(self):
        i = self.slider_temps.value()
        if i >= self.slider_temps.maximum():
            self.btn_lecture.setChecked(False)
            return
        self.slider_temps.setValue(i + 1)
        if self.btn_lecture.isChecked():
            self._minuteur.start(self._intervalle_lecture_ms())

    def save_png(self, path, resolution="1080p", fond="blanc", titre=None):
        largeur, hauteur = _TAILLES_EXPORT.get(
            resolution, _TAILLES_EXPORT["1080p"])
        transparent = fond == "transparent"
        if self.btn_3d.isChecked():
            acteur_titre = None
            if titre:
                acteur_titre = self.interactor.add_text(
                    titre, position="upper_edge", font_size=15,
                    name="titre_export_fieldlab")
            fond_avant = "#111827" if self._theme_sombre else "white"
            self.interactor.set_background(
                "white" if fond == "blanc" else fond_avant)
            try:
                self.interactor.screenshot(
                    path, window_size=(largeur, hauteur),
                    transparent_background=transparent)
            finally:
                self.interactor.set_background(fond_avant)
                if acteur_titre is not None:
                    try:
                        self.interactor.remove_actor(acteur_titre)
                    except (AttributeError, RuntimeError):
                        pass
        else:
            taille_avant = self.figure.get_size_inches().copy()
            titre_avant = (self.figure._suptitle.get_text()
                           if self.figure._suptitle is not None else None)
            dpi = 200
            self.figure.set_size_inches(largeur / dpi, hauteur / dpi)
            if titre:
                self.figure.suptitle(titre)
            if fond == "blanc":
                self.figure.set_facecolor("white")
                for axe in self.figure.axes:
                    axe.set_facecolor("white")
                    axe.tick_params(colors="#111827")
                    axe.xaxis.label.set_color("#111827")
                    axe.yaxis.label.set_color("#111827")
                    axe.title.set_color("#111827")
            try:
                self.figure.savefig(
                    path, dpi=dpi, transparent=transparent,
                    facecolor="none" if transparent else "white")
            finally:
                self.figure.set_size_inches(taille_avant)
                if titre_avant:
                    self.figure.suptitle(titre_avant)
                elif self.figure._suptitle is not None:
                    self.figure._suptitle.remove()
                    self.figure._suptitle = None
                self._styler_figure(self.figure)
                self.canvas.draw_idle()

    def image_png(self) -> bytes:
        flux = BytesIO()
        if self.btn_3d.isChecked():
            from PIL import Image
            pixels = np.asarray(
                self.interactor.screenshot(return_img=True), dtype=np.uint8)
            Image.fromarray(pixels).save(flux, format="PNG")
        else:
            self.figure.savefig(
                flux, format="png", dpi=180, bbox_inches="tight")
        return flux.getvalue()

    @staticmethod
    def _incruster_horodatage(image, secondes):
        from PIL import Image, ImageDraw

        image_pil = Image.fromarray(np.asarray(image, dtype=np.uint8)).convert("RGB")
        dessin = ImageDraw.Draw(image_pil)
        texte = f"t = {format_duree(secondes)}"
        boite = dessin.textbbox((0, 0), texte)
        largeur, hauteur = boite[2] - boite[0], boite[3] - boite[1]
        marge = max(12, image_pil.width // 120)
        xy = (marge, marge)
        dessin.rounded_rectangle(
            (xy[0] - 6, xy[1] - 5, xy[0] + largeur + 7,
             xy[1] + hauteur + 6), radius=5, fill=(17, 24, 39))
        dessin.text(xy, texte, fill="white")
        return np.asarray(image_pil)

    def export_video(self, path, duree_video=10.0, resolution="1080p",
                     horodatage=True):
        if self._transitoire is None:
            raise ValueError("Aucune animation active à exporter "
                              "(lancez d'abord une simulation transitoire ou variable).")
        import numpy as np
        import imageio.v2 as imageio

        largeur, hauteur = _TAILLES_EXPORT.get(
            resolution, _TAILLES_EXPORT["1080p"])
        nombre_images = len(self._transitoire.champs)
        fps = max(1.0, (nombre_images - 1) / max(float(duree_video), 0.1))
        index_avant = self.slider_temps.value()
        taille_figure_avant = self.figure.get_size_inches().copy()
        try:
            with imageio.get_writer(path, fps=fps) as writer:
                for i in range(nombre_images):
                    self.slider_temps.blockSignals(True)
                    self.slider_temps.setValue(i)
                    self.slider_temps.blockSignals(False)
                    self._afficher_instant(i)
                    if self.btn_3d.isChecked():
                        self.interactor.render()
                        image = self.interactor.screenshot(
                            return_img=True, window_size=(largeur, hauteur))
                    else:
                        self.figure.set_size_inches(largeur / 100, hauteur / 100)
                        self.canvas.draw()
                        image = np.asarray(self.canvas.buffer_rgba())[:, :, :3]
                    if horodatage:
                        image = self._incruster_horodatage(
                            image, self._transitoire.instants[i])
                    writer.append_data(image)
        finally:
            self.figure.set_size_inches(taille_figure_avant)
            self.slider_temps.blockSignals(True)
            self.slider_temps.setValue(index_avant)
            self.slider_temps.blockSignals(False)
            self._afficher_instant(index_avant)

    def reset(self):
        self._dernier_resultat = None
        self._dernier_kind = None
        self._apercu_2d_courant = None
        self._desactiver_lecteur()
        self._desactiver_sonde()
        self._desactiver_selection_scene()
        self._options_coupe_3d = fem3d_render.OptionsCoupe3D()
        self._options_rendu_3d = fem3d_render.OptionsRendu3D()
        self._calques_3d = fem3d_render.CalquesRendu3D()
        self._calques_2d = {
            "carte": True, "iso": False, "lignes": False, "fleches": False}
        self._fond_intensite_2d = False
        self._selection_scalaire_3d = "Scalaire principal"
        self._bornes_plans_3d = None
        self._extremites_sonde_ligne_3d = None
        self._sondes_2d = []
        self._points_profil_2d = []
        self._donnees_profil_2d = None
        self.btn_sonde_2d.setChecked(False)
        self.btn_profil_2d.setChecked(False)
        self._synchroniser_boutons_calques()
        self._appliquer_prereglage_calques_2d("Carte scalaire")
        self.cb_normale_coupe_3d.setCurrentText("X")
        self.slider_coupe_3d.setValue(50)
        self.spin_plans_coupe_3d.setValue(1)
        self.btn_isolignes_coupe_3d.setChecked(True)
        self.btn_vecteurs_coupe_3d.setChecked(False)
        self.btn_lignes_coupe_3d.setChecked(False)
        self.btn_manipuler_coupe_3d.setChecked(False)
        self.btn_clip_boite_3d.setChecked(False)
        self.spin_iso_3d.setValue(8)
        self.slider_iso_min_3d.setValue(5)
        self.slider_iso_max_3d.setValue(95)
        self.slider_source_lignes_3d.setValue(55)
        self.spin_densite_lignes_3d.setValue(7)
        self.slider_tubes_3d.setValue(4)
        self.spin_pas_glyphes_3d.setValue(4)
        self.slider_taille_glyphes_3d.setValue(12)
        self.cb_graines_3d.setCurrentText("Automatique")
        self.btn_graines_diag_3d.setChecked(False)
        self.btn_sonde_ligne_3d.setChecked(False)
        self._maj_controles_coupe_3d()
        self._maj_controles_p3()
        self._maj_barres_3d()
        if self.domaine.nom == "Magnetostatique":
            self.configurer_defaut_magnetique_3d(
                selectionner_intensite=False)
        self.profil_3d.hide()
        self.profil_2d.hide()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        self.interactor.clear()
        self._accueil()

    def _accueil(self):
        couleurs = theme_app.couleurs(self._theme_sombre)
        self.ax.text(0.5, 0.5,
                     f"{self.domaine.titre}\nConfigurez puis lancez la simulation",
                     ha="center", va="center", fontsize=13,
                     color=couleurs["texte_secondaire"])
        self.ax.set_axis_off()
        self._styler_figure(self.figure)
        self.canvas.draw()
        self.interactor.add_text(
            f"{self.domaine.titre}\nConfigurez puis lancez la simulation",
            position="upper_edge", font_size=10,
            color=couleurs["texte_secondaire"])
