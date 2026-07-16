import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from fieldlab.app.panels.electrostatique import ElectrostatiquePanel
from fieldlab.app.widgets_i18n import ComboBoxTraduit
from fieldlab.domaines import DOMAINES
from fieldlab.i18n import definir_langue, traduire_interface


@pytest.fixture(scope="module")
def application_qt():
    application = QApplication.instance() or QApplication([])
    yield application


class _ControleurMinimal:
    domaine = DOMAINES["Electrostatique"]
    _generation = 0
    result = None

    def run_simulation(self):
        pass

    def annuler(self):
        pass

    def reinitialiser(self):
        pass

    def refresh_plot(self, _kind):
        pass


def test_combo_traduit_garde_la_valeur_metier(application_qt):
    definir_langue("en")
    combo = ComboBoxTraduit()
    combo.addItems(["Stationnaire", "Transitoire"])
    assert combo.itemText(0) == "Steady state"
    assert combo.currentText() == "Stationnaire"
    combo.setCurrentText("Transitoire")
    assert combo.itemText(combo.currentIndex()) == "Transient"
    assert combo.currentText() == "Transitoire"
    combo.deleteLater()
    definir_langue("fr")


def test_panneau_bascule_fr_en_sans_changer_scenario(application_qt):
    definir_langue("fr")
    panneau = ElectrostatiquePanel(_ControleurMinimal())
    panneau.set_mode_interface("cours")
    scenario_interne = panneau.cb_geom.currentText()

    definir_langue("en")
    traduire_interface(panneau)
    assert panneau.run_btn.text() == "Simulate"
    assert panneau.run_btn.toolTip() == (
        "Computes the field using the displayed parameters.")
    assert panneau.cb_geom.currentText() == scenario_interne
    assert panneau.cb_geom.itemText(panneau.cb_geom.currentIndex()) != scenario_interne
    panneau._maj_validite()
    assert "Material properties are teaching-scale estimates" in (
        panneau.label_validite.text())
    panneau.set_mode_interface("expert")
    panneau.set_mode_interface("cours")
    assert panneau.run_btn.text() == "Simulate"

    definir_langue("fr")
    traduire_interface(panneau)
    assert panneau.run_btn.text() == "Simuler"
    assert panneau.cb_geom.itemText(panneau.cb_geom.currentIndex()) == scenario_interne
    panneau.deleteLater()
