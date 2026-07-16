import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from fieldlab.app.panels.electrostatique import ElectrostatiquePanel
from fieldlab.app.panels.thermique import ThermiquePanel
from fieldlab.domaines import DOMAINES
from fieldlab.geometries import NOM_SCENE_LIBRE_2D


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


def test_mode_cours_masque_jargon_et_garde_parametres_surs(application_qt):
    panneau = ElectrostatiquePanel(_ControleurMinimal())
    panneau.set_mode_interface("cours")
    assert panneau.cb_geom.currentText() != NOM_SCENE_LIBRE_2D
    assert panneau.cb_meth.currentText() == "FEM (direct)"
    assert panneau.spin_N.value() == 100
    assert panneau.spin_N.parentWidget().isHidden()
    assert panneau.groupe_solveur.isHidden()
    assert panneau.run_btn.text() == "Simuler"
    panneau.deleteLater()


def test_mode_expert_retablit_tous_les_scenarios(application_qt):
    panneau = ElectrostatiquePanel(_ControleurMinimal())
    panneau.set_mode_interface("cours")
    panneau.set_mode_interface("expert")
    noms = [panneau.cb_geom.itemText(i)
            for i in range(panneau.cb_geom.count())]
    assert noms == list(DOMAINES["Electrostatique"].scenarios)
    assert not panneau.spin_N.parentWidget().isHidden()
    assert panneau.run_btn.text() == "Lancer la simulation"
    panneau.deleteLater()


def test_fil_rouge_trempe_est_pret_en_mode_cours(application_qt):
    controleur = _ControleurMinimal()
    controleur.domaine = DOMAINES["Thermique"]
    panneau = ThermiquePanel(controleur)
    panneau.set_mode_interface("cours")
    panneau.cb_geom.setCurrentText("Trempe (objet chaud dans l'eau)")
    assert panneau.cb_environnement.currentText() == "Eau"
    assert panneau.spin_duree.value() == 2700.0
    assert panneau.cb_vitesse_lecture.currentData() == 1000
    panneau.deleteLater()
