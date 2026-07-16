import numpy as np
from fieldlab.boundary import appliquer_parois, restaurer_dirichlet
from fieldlab.solvers.base import moyenne_voisins


def omega_optimal(N):
    return 2.0 / (1.0 + np.sin(np.pi / N))


def make_step(omega):
    def step(field):
        w = omega
        V = field.V
        V_old = V.copy()
        terme = (field.h ** 2 / 4.0 * field.source
                 * getattr(field, "facteur_source", 1.0))
        moy = moyenne_voisins(V, field.fluid) + terme
        V[field.rouge] = (1 - w) * V[field.rouge] + w * moy[field.rouge]
        moy = moyenne_voisins(V, field.fluid) + terme
        V[field.noir] = (1 - w) * V[field.noir] + w * moy[field.noir]
        appliquer_parois(V, field.walls)
        restaurer_dirichlet(V, V_old, field.fixed_mask)
        return np.max(np.abs(V - V_old))
    return step
