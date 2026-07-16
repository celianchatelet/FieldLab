import numpy as np

from fieldlab import geometries, thermique
from fieldlab.fem.transient import resoudre_transitoire
from fieldlab.materials import MATERIAUX
from fieldlab.scenarios_pedagogiques import description_scenario, preset_2d


def test_scenarios_de_cours_requis_sont_declares():
    electro = {
        "Condensateur plan", "Dipole (deux disques)", "Cage de Faraday",
        "Pointe - plan (effet de pointe)",
        "Condensateur avec diélectrique partiel",
    }
    thermique_requis = {
        "Mur composite (verre + plastique)", "Ailette de refroidissement",
        "Trempe (objet chaud dans l'eau)", "Pont thermique",
        "Plancher chauffant",
    }
    assert electro <= set(geometries.GEOMETRIES)
    assert thermique_requis <= set(thermique.SCENARIOS)
    assert all(description_scenario(nom) for nom in electro | thermique_requis)


def test_dielectrique_partiel_injecte_epsilon_relative_du_verre():
    champ = geometries.build(
        geometries.GEOMETRIES,
        "Condensateur avec diélectrique partiel", N=51, val=100.0,
        kappa_fond=1.0006, taille_domaine=0.10)
    assert np.isclose(champ.kappa[15, 25], 7.0)
    assert np.isclose(champ.kappa[40, 25], 1.0006)


def test_mur_composite_utilise_deux_materiaux_reels():
    champ = geometries.build(
        thermique.SCENARIOS, "Mur composite (verre + plastique)",
        N=41, val=80.0,
        walls=thermique.walls_defaut(
            "Mur composite (verre + plastique)", 80.0),
        kappa_fond=0.026, rho_cp_fond=MATERIAUX["Air"].rho_cp)
    assert np.isclose(champ.kappa[20, 10], MATERIAUX["Verre"].kappa_thermique)
    assert np.isclose(
        champ.kappa[20, 30], MATERIAUX["Plastique"].kappa_thermique)


def test_trempe_refroidit_objet_sans_le_maintenir_a_temperature_imposee():
    eau = MATERIAUX["Eau"]
    champ = geometries.build(
        thermique.SCENARIOS, "Trempe (objet chaud dans l'eau)",
        N=25, val=80.0,
        walls=thermique.walls_defaut(
            "Trempe (objet chaud dans l'eau)", 80.0),
        kappa_fond=eau.kappa_thermique, rho_cp_fond=eau.rho_cp,
        taille_domaine=0.05)
    assert champ.initial_mask.any()
    assert not champ.fixed_mask.any()
    resultat = resoudre_transitoire(
        champ, T_initiale=15.0, dt=27.0, duree=2700.0, n_images=10)
    centre = float(resultat.champ.V[12, 12])
    eau_proche = float(resultat.champ.V[12, 17])
    assert 15.0 < centre < 80.0
    assert eau_proche > 15.0


def test_preset_trempe_correspond_au_fil_rouge():
    preset = preset_2d("Thermique", "Trempe (objet chaud dans l'eau)")
    assert preset["environnement"] == "Eau"
    assert preset["regime"] == "Transitoire"
    assert preset["duree"] == 2700.0
    assert preset["vitesse_lecture"] == 1000
