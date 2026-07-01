import numpy as np
from fieldlab.boundary import appliquer_parois, restaurer_dirichlet
from fieldlab.solvers.base import moyenne_voisins


def step(field):
    V = field.V
    V_old = V.copy()
    moy = moyenne_voisins(V_old, field.fluid)
    moy += field.h ** 2 / 4.0 * field.source
    V[field.free] = moy[field.free]
    appliquer_parois(V, field.walls)
    restaurer_dirichlet(V, V_old, field.fixed_mask)
    return np.max(np.abs(V - V_old))
