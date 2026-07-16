"""Dialogues compacts pour les exports destinés aux supports de cours."""

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit,
)

from fieldlab.app.widgets_i18n import ComboBoxTraduit as QComboBox
from fieldlab.i18n import traduire_interface

RESOLUTIONS = {
    "1080p (1920×1080)": "1080p",
    "1440p (2560×1440)": "1440p",
    "4K (3840×2160)": "4K",
}


class DialogueExportImage(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options de l'image")
        layout = QFormLayout(self)
        self.resolution = QComboBox()
        for libelle, valeur in RESOLUTIONS.items():
            self.resolution.addItem(libelle, valeur)
        self.fond = QComboBox()
        self.fond.addItem("Blanc", "blanc")
        self.fond.addItem("Transparent", "transparent")
        self.titre = QLineEdit()
        self.titre.setPlaceholderText("Facultatif")
        layout.addRow("Résolution", self.resolution)
        layout.addRow("Fond", self.fond)
        layout.addRow("Titre", self.titre)
        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        layout.addRow(boutons)
        traduire_interface(self)

    def options(self):
        return {
            "resolution": self.resolution.currentData(),
            "fond": self.fond.currentData(),
            "titre": self.titre.text().strip() or None,
        }


class DialogueExportAnimation(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options de l'animation")
        layout = QFormLayout(self)
        self.duree = QDoubleSpinBox()
        self.duree.setRange(1.0, 300.0)
        self.duree.setValue(10.0)
        self.duree.setSuffix(" s")
        self.resolution = QComboBox()
        for libelle, valeur in RESOLUTIONS.items():
            self.resolution.addItem(libelle, valeur)
        self.horodatage = QCheckBox("Afficher le vrai temps simulé")
        self.horodatage.setChecked(True)
        layout.addRow("Durée de la vidéo", self.duree)
        layout.addRow("Résolution", self.resolution)
        layout.addRow("Horodatage", self.horodatage)
        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        layout.addRow(boutons)
        traduire_interface(self)

    def options(self):
        return {
            "duree_video": float(self.duree.value()),
            "resolution": self.resolution.currentData(),
            "horodatage": bool(self.horodatage.isChecked()),
        }
