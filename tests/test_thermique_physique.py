import numpy as np

from fieldlab.fem.transient import resoudre_transitoire
from fieldlab.garde_fous import verifier_parametres
from fieldlab.grid import Field
from fieldlab.materials import MATERIAUX
from fieldlab.unites import (
    duree_diffusion_suggeree, format_duree, pas_temps_implicite,
)


def test_format_duree_adapte_automatiquement_unite():
    assert format_duree(0.850) == "850 ms"
    assert format_duree(12.4) == "12,4 s"
    assert format_duree(200) == "3 min 20 s"
    assert format_duree(8100) == "2 h 15 min"
    assert format_duree(3.2 * 86400) == "3,2 j"


def test_duree_eau_20_cm_est_de_plusieurs_heures():
    eau = MATERIAUX["Eau"]
    duree = duree_diffusion_suggeree(
        0.2, eau.kappa_thermique, eau.rho_cp)
    assert 6 * 3600 < duree < 48 * 3600


def test_pas_implicite_est_borne_sans_modifier_la_duree():
    dt, n_pas = pas_temps_implicite(7200.0, 500)
    assert n_pas == 2000
    assert np.isclose(dt * n_pas, 7200.0)


def test_milieu_normalise_est_bloque_en_transitoire_2d_et_3d():
    commun = {
        "method": "FEM (direct)", "N": 30, "N_3d": 8,
        "rho_cp_fond": 1.0, "environnement": "(aucun, vide normalise)",
    }
    blocages_2d, _ = verifier_parametres(
        commun | {"dimension": "2D", "regime": "Transitoire"},
        "Thermique")
    blocages_3d, _ = verifier_parametres(
        commun | {"dimension": "3D", "regime_3d": "Transitoire"},
        "Thermique")
    assert any("milieu physique réel" in message for message in blocages_2d)
    assert any("milieu physique réel" in message for message in blocages_3d)


def _solution_plaque_semi_isolee(x, temps, longueur, alpha, termes=120):
    """T(0)=1, dT/dx(L)=0 et T(x,0)=0."""

    resultat = np.ones_like(np.asarray(x, dtype=float))
    for n in range(termes):
        impair = 2 * n + 1
        valeur_propre = impair * np.pi / (2.0 * longueur)
        resultat -= (4.0 / (impair * np.pi)
                     * np.sin(valeur_propre * x)
                     * np.exp(-alpha * valeur_propre ** 2 * temps))
    return resultat


def test_diffusion_1d_eau_suit_solution_analytique():
    eau = MATERIAUX["Eau"]
    longueur = 0.2
    alpha = eau.kappa_thermique / eau.rho_cp
    tau = longueur ** 2 / alpha
    duree = tau / 4.0
    n = 25
    V = np.zeros((n, n))
    fixe = np.zeros((n, n), dtype=bool)
    fixe[:, 0] = True
    V[:, 0] = 1.0
    champ = Field(
        V, fixe, h=longueur / (n - 1),
        walls={cote: ("neumann",) for cote in
               ("haut", "bas", "gauche", "droite")},
        kappa=np.full((n, n), eau.kappa_thermique),
        rho_cp=np.full((n, n), eau.rho_cp),
        taille_domaine=longueur,
    )
    resultat = resoudre_transitoire(
        champ, T_initiale=0.0, dt=duree / 100.0,
        duree=duree, n_images=10)
    x = np.linspace(0.0, longueur, n)
    attendu = _solution_plaque_semi_isolee(
        x, duree, longueur, alpha)
    calcule = resultat.champ.V[n // 2]
    assert np.max(np.abs(calcule - attendu)) < 0.06
