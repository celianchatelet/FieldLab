import numpy as np


def appliquer_parois(V, walls):
    """Applique les conditions de bord non-Dirichlet.

    neumann : gradient nul (T_bord = T_premier_voisin_interieur).
    dirichlet : ignore ici, gere par fixed_mask + restaurer_dirichlet.
    Tout type inconnu est traite comme neumann.
    """
    for cote, spec in walls.items():
        if spec[0] == "dirichlet":
            continue
        if cote == "haut":     V[0, :]  = V[1, :]
        elif cote == "bas":    V[-1, :] = V[-2, :]
        elif cote == "gauche": V[:, 0]  = V[:, 1]
        elif cote == "droite": V[:, -1] = V[:, -2]
    return V


def restaurer_dirichlet(V, V_ref, fixed_mask):
    V[fixed_mask] = V_ref[fixed_mask]
    return V
