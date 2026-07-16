"""Widgets Qt dont l'affichage traduit ne change jamais la valeur métier."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox as _QComboBox

from fieldlab.i18n import tr


_ROLE_SOURCE = int(Qt.ItemDataRole.UserRole) + 77


class ComboBoxTraduit(_QComboBox):
    def addItem(self, texte, userData=None):
        super().addItem(str(texte), userData)
        self.setItemData(self.count() - 1, str(texte), _ROLE_SOURCE)
        self.setItemText(self.count() - 1, tr(str(texte)))

    def addItems(self, textes):
        for texte in textes:
            self.addItem(texte)

    def insertItem(self, index, texte, userData=None):
        super().insertItem(index, str(texte), userData)
        self.setItemData(index, str(texte), _ROLE_SOURCE)
        self.setItemText(index, tr(str(texte)))

    def currentText(self):
        source = self.itemData(self.currentIndex(), _ROLE_SOURCE)
        return str(source) if source is not None else super().currentText()

    def findText(self, texte, flags=Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive):
        for index in range(self.count()):
            if self.itemData(index, _ROLE_SOURCE) == texte:
                return index
        return super().findText(str(texte), flags)

    def setCurrentText(self, texte):
        index = self.findText(texte)
        if index >= 0:
            self.setCurrentIndex(index)
        else:
            super().setCurrentText(str(texte))

    def appliquer_langue(self):
        for index in range(self.count()):
            source = self.itemData(index, _ROLE_SOURCE)
            if source is not None:
                self.setItemText(index, tr(str(source)))
