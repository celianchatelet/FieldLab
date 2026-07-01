"""Scenarios de conduction thermique en regime permanent (nabla^2 T = 0).

Principe : uniquement des temperatures imposees (Dirichlet) et des parois
adiabatiques (Neumann). Aucune source de chaleur, aucune convection,
aucun rayonnement. La solution respecte le principe du maximum : T reste
toujours comprise entre la plus froide et la plus chaude des temperatures
imposees. Probleme bien pose et independant du maillage.

Les builders definissent le contenu interieur (blocs a temperature imposee,
inclusions isolantes internes). Les conditions sur le bord exterieur sont
gerees par le panneau "Parois" via walls_defaut(nom, val).
"""
import numpy as np

from fieldlab import obstacles as ob

COTES = ("haut", "bas", "gauche", "droite")


def _vides(N):
    return (np.zeros((N, N)), np.zeros((N, N), bool),
            np.zeros((N, N), bool), np.zeros((N, N)))


# --- builders : contenu interieur uniquement ------------------------------

def mur(N, T):
    """Gradient 1D : paroi gauche a T, paroi droite a 0. Profil lineaire exact."""
    return _vides(N)


def coin_chaud(N, T):
    """Coin chaud-chaud / coin froid-froid (diagonale)."""
    return _vides(N)


def quatre_parois(N, T):
    """Quatre parois a des temperatures differentes."""
    return _vides(N)


def tuyau_chaud(N, T):
    """Tuyau central a T ; l'enceinte froide vient des parois."""
    V, f, s, src = _vides(N)
    ob.disque(V, f, s, 0.50, 0.50, 0.12, ("dirichlet", T))
    return V, f, s, src


def doigt_froid(N, T):
    """Puits froid central a 0 ; le fond chaud vient des parois."""
    V, f, s, src = _vides(N)
    ob.disque(V, f, s, 0.50, 0.50, 0.10, ("dirichlet", 0.0))
    return V, f, s, src


def echangeur(N, T):
    """Obstacle isolant central ; le gradient chaud/froid vient des parois.
    L'inclusion isolante est un ingredient interne du scenario (non exposee
    dans la palette utilisateur)."""
    V, f, s, src = _vides(N)
    ob.disque(V, f, s, 0.50, 0.50, 0.13, ("isolant",))
    return V, f, s, src


def pont_thermique(N, T):
    """Paroi isolante percee d'un etroit pont conducteur ; chaud/froid via les parois.
    Les inclusions isolantes sont internes au scenario."""
    V, f, s, src = _vides(N)
    ob.rectangle(V, f, s, 0.47, 0.00, 0.53, 0.40, ("isolant",))
    ob.rectangle(V, f, s, 0.47, 0.60, 0.53, 1.00, ("isolant",))
    return V, f, s, src


def composant_chaud(N, T):
    """Bloc central a T entour de parois froides.

    Remplace l'ancien scenario a source de chaleur : la temperature du bloc
    est imposee (Dirichlet), ce qui garantit T in [0, T].
    """
    V, f, s, src = _vides(N)
    ob.rectangle(V, f, s, 0.41, 0.41, 0.59, 0.59, ("dirichlet", T))
    return V, f, s, src


def deux_blocs_chauds(N, T):
    """Deux blocs chauds a T symetriques dans une enceinte froide."""
    V, f, s, src = _vides(N)
    ob.rectangle(V, f, s, 0.26, 0.43, 0.40, 0.57, ("dirichlet", T))
    ob.rectangle(V, f, s, 0.60, 0.43, 0.74, 0.57, ("dirichlet", T))
    return V, f, s, src


def processeur_chaud(N, T):
    """Quatre blocs chauds a T disposes en carre dans une enceinte froide."""
    V, f, s, src = _vides(N)
    for cx, cy in ((0.29, 0.29), (0.71, 0.29), (0.29, 0.71), (0.71, 0.71)):
        ob.disque(V, f, s, cx, cy, 0.09, ("dirichlet", T))
    return V, f, s, src


SCENARIOS = {
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
}

NOMS = list(SCENARIOS)


def walls_defaut(nom, val):
    """Parois recommandees par scenario (modifiables ensuite dans l'UI)."""
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
    }
    return table.get(nom, {c: N for c in COTES})
