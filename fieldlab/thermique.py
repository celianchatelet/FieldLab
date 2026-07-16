import numpy as np

from fieldlab import obstacles as ob
from fieldlab.geometries import NOM_SCENE_LIBRE_2D
from fieldlab.materials import MATERIAUX

COTES = ("haut", "bas", "gauche", "droite")


def _vides(N):
    return (np.zeros((N, N)), np.zeros((N, N), bool),
            np.zeros((N, N), bool), np.zeros((N, N)))


def scene_libre(N, T):
    return _vides(N)




def mur(N, T):
    return _vides(N)


def coin_chaud(N, T):
    return _vides(N)


def quatre_parois(N, T):
    return _vides(N)


def tuyau_chaud(N, T):
    V, f, s, src = _vides(N)
    ob.disque(V, f, s, 0.50, 0.50, 0.12, ("dirichlet", T))
    return V, f, s, src


def doigt_froid(N, T):
    V, f, s, src = _vides(N)
    ob.disque(V, f, s, 0.50, 0.50, 0.10, ("dirichlet", 0.0))
    return V, f, s, src


def echangeur(N, T):
    V, f, s, src = _vides(N)
    ob.disque(V, f, s, 0.50, 0.50, 0.13, ("isolant",))
    return V, f, s, src


def pont_thermique(N, T):
    V, f, s, src = _vides(N)
    ob.rectangle(V, f, s, 0.47, 0.00, 0.53, 0.40, ("isolant",))
    ob.rectangle(V, f, s, 0.47, 0.60, 0.53, 1.00, ("isolant",))
    return V, f, s, src


def composant_chaud(N, T):
    V, f, s, src = _vides(N)
    ob.rectangle(V, f, s, 0.41, 0.41, 0.59, 0.59, ("dirichlet", T))
    return V, f, s, src


def deux_blocs_chauds(N, T):
    V, f, s, src = _vides(N)
    ob.rectangle(V, f, s, 0.26, 0.43, 0.40, 0.57, ("dirichlet", T))
    ob.rectangle(V, f, s, 0.60, 0.43, 0.74, 0.57, ("dirichlet", T))
    return V, f, s, src


def processeur_chaud(N, T):
    V, f, s, src = _vides(N)
    for cx, cy in ((0.29, 0.29), (0.71, 0.29), (0.29, 0.71), (0.71, 0.71)):
        ob.disque(V, f, s, cx, cy, 0.09, ("dirichlet", T))
    return V, f, s, src


def mur_composite(N, T):
    V, f, s, src = _vides(N)
    verre, plastique = MATERIAUX["Verre"], MATERIAUX["Plastique"]
    kappa = np.empty_like(V)
    rho_cp = np.empty_like(V)
    separation = N // 2
    kappa[:, :separation] = verre.kappa_thermique
    kappa[:, separation:] = plastique.kappa_thermique
    rho_cp[:, :separation] = verre.rho_cp
    rho_cp[:, separation:] = plastique.rho_cp
    return V, f, s, src, kappa, rho_cp


def ailette_refroidissement(N, T):
    V, f, s, src = _vides(N)
    aluminium = MATERIAUX["Aluminium"]
    kappa = np.full_like(V, np.nan)
    rho_cp = np.full_like(V, np.nan)
    y0, y1, x0, x1 = (int(v * N) for v in (0.43, 0.57, 0.05, 0.90))
    kappa[y0:y1, x0:x1] = aluminium.kappa_thermique
    rho_cp[y0:y1, x0:x1] = aluminium.rho_cp
    ob.rectangle(V, f, s, 0.05, 0.43, 0.09, 0.57,
                 ("dirichlet", T))
    return V, f, s, src, kappa, rho_cp


def trempe(N, T):
    """Objet de cuivre chaud libre de refroidir dans le milieu de fond."""

    V, f, s, src = _vides(N)
    cuivre = MATERIAUX["Cuivre"]
    kappa = np.full_like(V, np.nan)
    rho_cp = np.full_like(V, np.nan)
    Y, X = np.ogrid[:N, :N]
    masque = ((X - 0.5 * (N - 1)) ** 2 + (Y - 0.5 * (N - 1)) ** 2
              <= (0.12 * N) ** 2)
    V[masque] = float(T)
    kappa[masque] = cuivre.kappa_thermique
    rho_cp[masque] = cuivre.rho_cp
    return V, f, s, src, kappa, rho_cp, masque


def plancher_chauffant(N, T):
    V, f, s, src = _vides(N)
    # Béton courant : k ≈ 1,4 W/m/K et ρcp ≈ 2,0 MJ/m³/K.
    kappa = np.full_like(V, 1.4)
    rho_cp = np.full_like(V, 2.0e6)
    src[int(0.08 * N):int(0.12 * N), int(0.08 * N):int(0.92 * N)] = 500.0
    return V, f, s, src, kappa, rho_cp


SCENARIOS = {
    NOM_SCENE_LIBRE_2D:                  scene_libre,
    "Mur (gradient 1D)":            mur,
    "Coin chaud":                    coin_chaud,
    "Quatre parois":                 quatre_parois,
    "Tuyau chaud (enceinte froide)": tuyau_chaud,
    "Doigt froid (puits central)":   doigt_froid,
    "Echangeur (obstacle isolant)":  echangeur,
    "Pont thermique":                pont_thermique,
    "Composant chaud":               composant_chaud,
    "Deux blocs chauds":             deux_blocs_chauds,
    "Processeur (4 blocs chauds)":   processeur_chaud,
    "Mur composite (verre + plastique)": mur_composite,
    "Ailette de refroidissement": ailette_refroidissement,
    "Trempe (objet chaud dans l'eau)": trempe,
    "Plancher chauffant": plancher_chauffant,
}

NOMS = list(SCENARIOS)


def walls_defaut(nom, val):
    N = ("neumann",)
    def D(x):
        return ("dirichlet", float(x))
    chaud, froid = val, 0.0
    table = {
        "Mur (gradient 1D)":
            {"gauche": D(chaud), "droite": D(froid), "haut": N, "bas": N},
        "Coin chaud":
            {"gauche": D(chaud), "bas": D(chaud), "droite": D(froid), "haut": D(froid)},
        "Quatre parois":
            {"gauche": D(chaud), "droite": D(froid),
             "bas":    D(0.7 * chaud), "haut": D(0.3 * chaud)},
        "Tuyau chaud (enceinte froide)":
            {c: D(froid) for c in COTES},
        "Doigt froid (puits central)":
            {c: D(chaud) for c in COTES},
        "Echangeur (obstacle isolant)":
            {"gauche": D(chaud), "droite": D(froid), "haut": N, "bas": N},
        "Pont thermique":
            {"gauche": D(chaud), "droite": D(froid), "haut": N, "bas": N},
        "Composant chaud":
            {c: D(froid) for c in COTES},
        "Deux blocs chauds":
            {c: D(froid) for c in COTES},
        "Processeur (4 blocs chauds)":
            {c: D(froid) for c in COTES},
        "Mur composite (verre + plastique)":
            {"gauche": D(chaud), "droite": D(20.0), "haut": N, "bas": N},
        "Ailette de refroidissement":
            {c: ("robin", 8.0, 20.0) for c in COTES},
        "Trempe (objet chaud dans l'eau)":
            {c: N for c in COTES},
        "Plancher chauffant":
            {"gauche": N, "droite": N, "bas": N,
             "haut": ("robin", 8.0, 20.0)},
    }
    return table.get(nom, {c: N for c in COTES})
