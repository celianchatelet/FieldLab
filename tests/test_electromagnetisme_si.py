import numpy as np

from fieldlab import biot_savart, geometries, magneto
from fieldlab.constantes import EPSILON_0, MU_0, facteur_source_poisson
from fieldlab.fem.poisson import solve_poisson_from_field
from fieldlab.field import champ_electrique, champ_magnetique
from fieldlab.grid import Field
from fieldlab.materials import MATERIAUX


def _champ_plaque_1d(n, longueur, gauche, droite, source=0.0,
                     facteur_source=1.0):
    V = np.zeros((n, n))
    fixe = np.zeros((n, n), dtype=bool)
    fixe[:, 0] = fixe[:, -1] = True
    V[:, 0], V[:, -1] = gauche, droite
    return Field(
        V, fixe, h=longueur / (n - 1),
        source=np.full((n, n), source),
        kappa=np.ones((n, n)), taille_domaine=longueur,
        facteur_source=facteur_source,
    )


def test_condensateur_plan_respecte_v_egal_e_fois_d():
    longueur, tension = 0.12, 24.0
    champ0 = _champ_plaque_1d(41, longueur, tension, 0.0)
    resultat = solve_poisson_from_field(champ0)
    _ex, _ey, norme = champ_electrique(resultat.champ)
    attendu = tension / longueur
    calcule = np.median(norme[5:-5, 5:-5])
    assert abs(calcule / attendu - 1.0) < 0.01


def test_charge_volumique_est_divisee_par_epsilon_0():
    longueur = 0.10
    rho = 1.0e-9
    champ0 = _champ_plaque_1d(
        41, longueur, 0.0, 0.0, source=rho,
        facteur_source=facteur_source_poisson("Electrostatique"))
    resultat = solve_poisson_from_field(champ0)
    attendu_centre = rho * longueur ** 2 / (8.0 * EPSILON_0)
    calcule_centre = float(resultat.champ.V[20, 20])
    assert abs(calcule_centre / attendu_centre - 1.0) < 0.02


def test_fil_infini_2d_donne_b_en_teslas_a_cinq_pourcent():
    n, longueur, rayon = 121, 1.0, 0.05
    intensite = 5.0
    densite = intensite / (np.pi * rayon ** 2)
    champ0 = geometries.build(
        magneto.SCENARIOS, "Fil unique", N=n, val=densite,
        walls=magneto.walls_defaut("Fil unique", densite),
        taille_domaine=longueur,
        facteur_source=facteur_source_poisson("Magnetostatique"))
    resultat = solve_poisson_from_field(champ0)
    _bx, _by, norme = champ_magnetique(resultat.champ)
    distance = 0.15
    colonne = int(round((0.5 + distance / longueur) * (n - 1)))
    calcule = float(norme[n // 2, colonne])
    courant_discret = float(champ0.source.sum() * champ0.h ** 2)
    attendu = MU_0 * courant_discret / (2.0 * np.pi * distance)
    assert abs(calcule / attendu - 1.0) < 0.05


def test_kappa_magnetique_du_fond_et_du_noyau_est_injectee():
    noyau = {
        "forme": "disque", "args": {"cx": 0.5, "cy": 0.5, "r": 0.1},
        "bc": ("materiau", MATERIAUX["Fer"].kappa_magnetique),
    }
    champ = geometries.build(
        magneto.SCENARIOS, "Fil unique", N=41, val=1.0,
        obstacles=[noyau],
        kappa_fond=MATERIAUX["Air"].kappa_magnetique,
        facteur_source=facteur_source_poisson("Magnetostatique"))
    assert np.isclose(champ.kappa[0, 0], 1.0)
    assert np.isclose(champ.kappa[20, 20], 1.0 / 5000.0)


def test_biot_savart_fil_long_retrouve_loi_en_un_sur_r():
    courant, distance = 5.0, 0.2
    fil = biot_savart.fil_droit([0.0, 0.0, -100.0],
                                [0.0, 0.0, 100.0])
    B = biot_savart.champ_segments(
        fil, courant, np.array([[distance, 0.0, 0.0]]))[0]
    attendu = MU_0 * courant / (2.0 * np.pi * distance)
    assert abs(np.linalg.norm(B) / attendu - 1.0) < 1.0e-4
