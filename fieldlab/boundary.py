import numpy as np


def appliquer_parois(V, walls):
    for cote, spec in walls.items():
        if spec[0] == "dirichlet":
            continue
        if cote == "haut":     V[-1, :] = V[-2, :]
        elif cote == "bas":    V[0, :]  = V[1, :]
        elif cote == "gauche": V[:, 0]  = V[:, 1]
        elif cote == "droite": V[:, -1] = V[:, -2]
    return V


def restaurer_dirichlet(V, V_ref, fixed_mask):
    V[fixed_mask] = V_ref[fixed_mask]
    return V
