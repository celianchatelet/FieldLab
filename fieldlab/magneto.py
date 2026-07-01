"""Scenarios de magnetostatique 2D (∇²A_z = -µ0 J_z, courants selon z).

Les builders ne posent QUE les courants (sources). Le cadre A_z = 0 qui
confine le flux est gere par les parois (walls_defaut -> Dirichlet 0 partout),
donc modifiable depuis l'UI.
"""
import numpy as np

COTES = ("haut", "bas", "gauche", "droite")


def _vides(N):
    return (np.zeros((N, N)), np.zeros((N, N), bool),
            np.zeros((N, N), bool), np.zeros((N, N)))


def _fil(src, cx, cy, r, J):
    N = src.shape[0]
    Y, X = np.ogrid[:N, :N]
    m = (X - cx * N) ** 2 + (Y - cy * N) ** 2 <= (r * N) ** 2
    src[m] = J


def _barre(src, x0, x1, y0, y1, J):
    N = src.shape[0]
    src[int(y0 * N):int(y1 * N), int(x0 * N):int(x1 * N)] = J


def fil_unique(N, J):
    V, f, s, src = _vides(N)
    _fil(src, 0.50, 0.50, 0.05, J)
    return V, f, s, src


def deux_fils_opposes(N, J):
    V, f, s, src = _vides(N)
    _fil(src, 0.35, 0.50, 0.05, +J)
    _fil(src, 0.65, 0.50, 0.05, -J)
    return V, f, s, src


def deux_fils_meme_sens(N, J):
    V, f, s, src = _vides(N)
    _fil(src, 0.35, 0.50, 0.05, J)
    _fil(src, 0.65, 0.50, 0.05, J)
    return V, f, s, src


def boucle(N, J):
    V, f, s, src = _vides(N)
    _fil(src, 0.50, 0.42, 0.04, +J)
    _fil(src, 0.50, 0.58, 0.04, -J)
    return V, f, s, src


def quadripole(N, J):
    V, f, s, src = _vides(N)
    _fil(src, 0.35, 0.35, 0.045, +J)
    _fil(src, 0.65, 0.35, 0.045, -J)
    _fil(src, 0.35, 0.65, 0.045, -J)
    _fil(src, 0.65, 0.65, 0.045, +J)
    return V, f, s, src


def solenoide(N, J):
    V, f, s, src = _vides(N)
    _barre(src, 0.32, 0.38, 0.20, 0.80, +J)
    _barre(src, 0.62, 0.68, 0.20, 0.80, -J)
    return V, f, s, src


def nappe_courant(N, J):
    V, f, s, src = _vides(N)
    _barre(src, 0.20, 0.80, 0.47, 0.53, J)
    return V, f, s, src


SCENARIOS = {
    "Fil unique": fil_unique,
    "Deux fils (opposes)": deux_fils_opposes,
    "Deux fils (meme sens)": deux_fils_meme_sens,
    "Boucle de courant (dipole)": boucle,
    "Quadripole magnetique": quadripole,
    "Solenoide (coupe)": solenoide,
    "Nappe de courant": nappe_courant,
}

NOMS = list(SCENARIOS)


def walls_defaut(nom, val):
    """Cadre A_z = 0 (Dirichlet) sur les 4 bords : confine le flux dans la
    boite. Modifiable dans l'UI (en Neumann, le champ "sort" de la boite)."""
    return {c: ("dirichlet", 0.0) for c in COTES}
