import numpy as np
from fieldlab.boundary import appliquer_parois, restaurer_dirichlet
from fieldlab.solvers.base import moyenne_voisins


def step(field):
    V = field.V
    V_old = V.copy()
    terme = field.h ** 2 / 4.0 * field.source
    moy = moyenne_voisins(V, field.fluid) + terme
    V[field.rouge] = moy[field.rouge]
    moy = moyenne_voisins(V, field.fluid) + terme
    V[field.noir] = moy[field.noir]
    appliquer_parois(V, field.walls)
    restaurer_dirichlet(V, V_old, field.fixed_mask)
    return np.max(np.abs(V - V_old))
