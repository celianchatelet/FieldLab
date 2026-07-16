import sys
import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QComboBox, QDockWidget, QFileDialog,
    QLabel, QMainWindow, QMessageBox, QStackedWidget, QTabWidget,
)

from fieldlab.domaines import DOMAINES
from fieldlab.app import theme
from fieldlab.app.domain_controller import DomainController
from fieldlab.i18n import definir_langue, tr, traduire_interface
from fieldlab.ressources import chemin_ressource


class _FiltreMolette(QObject):
    def eventFilter(self, objet, evenement):
        if evenement.type() == QEvent.Type.Wheel and isinstance(
                objet, (QComboBox, QAbstractSpinBox)):
            evenement.ignore()
            return True
        return super().eventFilter(objet, evenement)


class FieldLabApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self._filtre_molette = _FiltreMolette(self)
        self.settings = QSettings("FieldLab", "FieldLab")
        self._langue = str(self.settings.value("interface/langue", "fr"))
        definir_langue(self._langue)
        QApplication.instance().installEventFilter(self._filtre_molette)
        self.setWindowTitle("FieldLab — Simulateur multiphysique 2D/3D")
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)

        self.controllers = {}
        self._dock_visible_avant_cours = True
        self._controllers_ordre = []
        self.tabs = QTabWidget()
        self.controls_stack = QStackedWidget()

        for nom, dom in DOMAINES.items():
            controller = DomainController(dom, parent=self)
            self.controllers[nom] = controller
            self._controllers_ordre.append(controller)
            self.tabs.addTab(controller.plot, dom.titre)
            self.controls_stack.addWidget(controller.panel)

        self.setCentralWidget(self.tabs)

        self.controls_dock = QDockWidget("Contrôles", self)
        self.controls_dock.setObjectName("controls_dock")
        self.controls_dock.setWidget(self.controls_stack)
        self.controls_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.controls_dock)

        self.tabs.currentChanged.connect(self.controls_stack.setCurrentIndex)

        self._build_menu()
        mode_initial = str(self.settings.value(
            "interface/mode", "cours"))
        self.act_mode_expert.setChecked(mode_initial == "expert")
        self._basculer_mode_expert(mode_initial == "expert")
        self.act_theme.setChecked(
            str(self.settings.value("interface/theme_sombre", "true")).lower()
            in {"1", "true", "yes"})
        self._changer_langue(self._langue)

    def _active_controller(self):
        index = self.tabs.currentIndex()
        if 0 <= index < len(self._controllers_ordre):
            return self._controllers_ordre[index]
        return None

    def _export(self, methode: str):
        controller = self._active_controller()
        if controller is None:
            QMessageBox.information(
                self, tr("Export indisponible"),
                tr("Aucun export disponible pour cet onglet."))
            return
        getattr(controller, methode)(self)

    def _build_menu(self):
        bar = self.menuBar()

        m_fichier = bar.addMenu("&Fichier")
        act_ouvrir = QAction("Ouvrir un projet FieldLab...", self)
        act_ouvrir.setShortcut("Ctrl+O")
        act_ouvrir.triggered.connect(self.ouvrir_projet)
        m_fichier.addAction(act_ouvrir)
        act_sauver = QAction("Sauvegarder le projet FieldLab...", self)
        act_sauver.setShortcut("Ctrl+S")
        act_sauver.triggered.connect(self.sauvegarder_projet)
        m_fichier.addAction(act_sauver)
        m_fichier.addSeparator()
        act_png = QAction("Exporter la figure (PNG)...", self)
        act_png.triggered.connect(lambda: self._export("export_png"))
        m_fichier.addAction(act_png)
        act_csv = QAction("Exporter le champ scalaire (CSV)...", self)
        act_csv.triggered.connect(lambda: self._export("export_csv"))
        m_fichier.addAction(act_csv)
        act_video = QAction("Exporter l'animation (vidéo/GIF)...", self)
        act_video.triggered.connect(lambda: self._export("export_video"))
        m_fichier.addAction(act_video)
        act_rapport = QAction("Exporter un rapport pédagogique (HTML)...", self)
        act_rapport.triggered.connect(lambda: self._export("export_rapport"))
        m_fichier.addAction(act_rapport)
        m_fichier.addSeparator()
        act_quit = QAction("Quitter", self)
        act_quit.triggered.connect(self.close)
        m_fichier.addAction(act_quit)

        m_affichage = bar.addMenu("&Affichage")
        self.act_theme = QAction("Thème sombre", self)
        self.act_theme.setCheckable(True)
        self.act_theme.toggled.connect(self._toggle_theme)
        m_affichage.addAction(self.act_theme)
        act_dock = self.controls_dock.toggleViewAction()
        act_dock.setText("Panneau Contrôles")
        m_affichage.addAction(act_dock)
        self.act_mode_expert = QAction("Mode Expert", self)
        self.act_mode_expert.setCheckable(True)
        self.act_mode_expert.toggled.connect(self._basculer_mode_expert)
        m_affichage.addAction(self.act_mode_expert)
        self.act_presentation = QAction("Présentation plein écran", self)
        self.act_presentation.setCheckable(True)
        self.act_presentation.setShortcut("F11")
        self.act_presentation.toggled.connect(self._basculer_presentation)
        m_affichage.addAction(self.act_presentation)

        m_langue = bar.addMenu("Langue / Language")
        groupe_langue = QActionGroup(self)
        groupe_langue.setExclusive(True)
        self.act_langue_fr = QAction("Français", self, checkable=True)
        self.act_langue_en = QAction("Anglais", self, checkable=True)
        groupe_langue.addAction(self.act_langue_fr)
        groupe_langue.addAction(self.act_langue_en)
        self.act_langue_fr.triggered.connect(
            lambda: self._changer_langue("fr"))
        self.act_langue_en.triggered.connect(
            lambda: self._changer_langue("en"))
        m_langue.addActions(groupe_langue.actions())
        self._groupe_langue = groupe_langue

        barre_mode = self.addToolBar("Mode d'interface")
        barre_mode.setObjectName("barre_mode_interface")
        self.label_mode_interface = QLabel("Mode : Cours")
        barre_mode.addWidget(self.label_mode_interface)
        barre_mode.addSeparator()
        barre_mode.addAction(self.act_mode_expert)

        m_analyse = bar.addMenu("&Analyse")
        act_indicateurs = QAction("Indicateurs physiques...", self)
        act_indicateurs.triggered.connect(
            lambda: self._export("afficher_analyse"))
        m_analyse.addAction(act_indicateurs)
        act_reference = QAction("Mémoriser le résultat comme référence A", self)
        act_reference.triggered.connect(
            lambda: self._export("memoriser_reference"))
        m_analyse.addAction(act_reference)
        act_comparer = QAction("Comparer le résultat courant B à A...", self)
        act_comparer.triggered.connect(
            lambda: self._export("comparer_reference"))
        m_analyse.addAction(act_comparer)

        m_aide = bar.addMenu("&Aide")
        act_about = QAction("À propos", self)
        act_about.triggered.connect(self._about)
        m_aide.addAction(act_about)
        act_limites = QAction("Afficher les hypothèses du modèle", self)
        act_limites.triggered.connect(self._afficher_limites)
        m_aide.addAction(act_limites)

    def sauvegarder_projet(self):
        chemin, _ = QFileDialog.getSaveFileName(
            self, tr("Sauvegarder le projet"), "",
            tr("Projet FieldLab (*.fieldlab.json);;JSON (*.json)"))
        if not chemin:
            return
        if not chemin.lower().endswith(".json"):
            chemin += ".fieldlab.json"
        projet = {
            "format": "fieldlab-project",
            "version": 1,
            "theme_sombre": bool(self.act_theme.isChecked()),
            "mode_interface": (
                "expert" if self.act_mode_expert.isChecked() else "cours"),
            "onglet_actif": int(self.tabs.currentIndex()),
            "domaines": {
                nom: controleur.panel.exporter_configuration()
                for nom, controleur in self.controllers.items()
            },
        }
        try:
            Path(chemin).write_text(
                json.dumps(projet, ensure_ascii=False, indent=2),
                encoding="utf-8")
            self.statusBar().showMessage(
                tr(f"Projet sauvegardé : {chemin}"), 6000)
        except (OSError, TypeError, ValueError) as erreur:
            QMessageBox.critical(
                self, tr("Sauvegarde impossible"), tr(str(erreur)))

    def ouvrir_projet(self):
        chemin, _ = QFileDialog.getOpenFileName(
            self, tr("Ouvrir un projet"), "",
            tr("Projet FieldLab (*.fieldlab.json *.json);;JSON (*.json)"))
        if not chemin:
            return
        try:
            projet = json.loads(Path(chemin).read_text(encoding="utf-8"))
            if projet.get("format") != "fieldlab-project":
                raise ValueError("Ce fichier n'est pas un projet FieldLab.")
            if int(projet.get("version", 0)) > 1:
                raise ValueError(
                    "Ce projet a été créé par une version plus récente de FieldLab.")
            for nom, configuration in projet.get("domaines", {}).items():
                if nom in self.controllers:
                    self.controllers[nom].panel.charger_configuration(
                        configuration)
                    self.controllers[nom].reinitialiser_resultat_seul()
                    panel = self.controllers[nom].panel
                    if panel.SUPPORTE_3D \
                            and panel.cb_dimension.currentText() == "3D":
                        panel._apercu_scene_3d()
            self.tabs.setCurrentIndex(max(
                0, min(int(projet.get("onglet_actif", 0)),
                       self.tabs.count() - 1)))
            self.act_theme.setChecked(
                bool(projet.get("theme_sombre", True)))
            self.act_mode_expert.setChecked(
                projet.get("mode_interface", "cours") == "expert")
            self.statusBar().showMessage(
                tr(f"Projet chargé : {chemin} — relancez les simulations."),
                7000)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as erreur:
            QMessageBox.critical(
                self, tr("Ouverture impossible"), tr(str(erreur)))

    def _basculer_mode_expert(self, actif):
        mode = "expert" if actif else "cours"
        self.settings.setValue("interface/mode", mode)
        if hasattr(self, "label_mode_interface"):
            source = "Mode : Expert" if actif else "Mode : Cours"
            self.label_mode_interface.setProperty("_i18n_source_text", source)
            self.label_mode_interface.setText(tr(source))
        for controller in self._controllers_ordre:
            controller.panel.set_mode_interface(mode)
        self.controls_dock.show()

    def _changer_langue(self, langue):
        """Retraduit l'interface sans changer les identifiants des modèles."""

        self._langue = langue
        definir_langue(langue)
        self.settings.setValue("interface/langue", langue)
        self.act_langue_fr.setChecked(langue == "fr")
        self.act_langue_en.setChecked(langue == "en")
        traduire_interface(self)
        for controller in self._controllers_ordre:
            controller.panel._maj_disponibilite_edition_2d()
            controller.panel._maj_validite()
            if controller.panel.SUPPORTE_3D:
                controller.panel._maj_disponibilite_edition_3d()

    def _basculer_presentation(self, actif):
        if actif:
            self._dock_visible_avant_cours = self.controls_dock.isVisible()
            self.controls_dock.hide()
            self.menuBar().hide()
            self.showFullScreen()
        else:
            self.showNormal()
            self.menuBar().show()
            self.controls_dock.setVisible(self._dock_visible_avant_cours)

    def _afficher_limites(self):
        controller = self._active_controller()
        if controller is None:
            return
        controller.panel.groupe_validite.setChecked(True)
        controller.panel.scroll.ensureWidgetVisible(
            controller.panel.groupe_validite)
        self.controls_dock.show()

    def _toggle_theme(self, dark):
        self.settings.setValue("interface/theme_sombre", bool(dark))
        theme.apply_theme(QApplication.instance(), dark)
        for controller in self._controllers_ordre:
            controller._annulation.set()
            try:
                controller.plot.appliquer_theme(dark)
            except (AttributeError, RuntimeError):
                pass

    def closeEvent(self, event):
        for controller in self._controllers_ordre:
            try:
                controller.plot.interactor.close()
            except (AttributeError, RuntimeError):
                pass
        super().closeEvent(event)

    def _about(self):
        texte = (
            "FieldLab — Simulateur multiphysique 2D/3D\n\n"
            "Champs électriques, magnétiques et thermiques :\n"
            "équations de Laplace/Poisson en 2D (différences finies et FEM)\n"
            "et en 3D (FEM tétraédrique), régimes statique, variable\n"
            "et transitoire, obstacles et matériaux réels.\n\n"
            "Un onglet par domaine, panneau de contrôle dockable,\n"
            "bascule 2D/3D dans chaque panneau.")
        QMessageBox.information(
            self, tr("À propos"), tr(texte))


def run():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(chemin_ressource(
        "assets", "fieldlab_icon.png"))))
    theme.apply_theme(app, dark=True)
    window = FieldLabApp()
    window.show()
    sys.exit(app.exec())
