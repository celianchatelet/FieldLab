from dataclasses import dataclass, field
from time import perf_counter

import numpy as np
import scipy.sparse.linalg as spla
import skfem

from fieldlab.annulation import verifier
from fieldlab.fem.mesh import unit_square_mesh
from fieldlab.fem.poisson import (
    _KAPPA_ISOLANT, _appliquer_robin, _extraire_grille_base, _laplace_kappa,
    _load, _resample_field_on_mesh,
)
from fieldlab.grid import Field


@skfem.BilinearForm
def _masse(u, v, w):
    return u * v


@skfem.BilinearForm
def _masse_ponderee(u, v, w):
    return w["rho_cp"] * u * v


@dataclass
class TransientResult:
    champs: list
    instants: list
    dt: float
    temps: float = 0.0
    converge: bool = True
    iterations: int = 0
    erreur: float = 0.0
    historique: list = field(default_factory=list)

    @property
    def champ(self) -> Field:
        return self.champs[-1]


def resoudre_transitoire(field0: Field, T_initiale: float, dt: float,
                          duree: float, n_images: int = 60,
                          refine: int = 0, progress=None,
                          annule=None) -> TransientResult:
    if dt <= 0:
        raise ValueError("Le pas de temps doit etre strictement positif.")
    if duree <= 0:
        raise ValueError("La duree simulee doit etre strictement positive.")
    if n_images < 1:
        raise ValueError("Le nombre d'images doit etre au moins 1.")

    n_base = field0.N - 1
    mesh = unit_square_mesh(n_base, refine=refine)
    basis = skfem.Basis(mesh, skfem.ElementTriP1())

    fixed_nodal, v_nodal, solid_nodal, source_nodal, kappa_materiau_nodal, _i, _j = \
        _resample_field_on_mesh(field0, n_base, basis.doflocs)
    kappa_nodal = np.where(solid_nodal, _KAPPA_ISOLANT, kappa_materiau_nodal)
    rho_cp_2d = getattr(field0, "rho_cp", None)
    rho_cp_nodal = (rho_cp_2d[_i, _j] if rho_cp_2d is not None
                    else np.ones(basis.N))







    L = float(getattr(field0, "taille_domaine", 1.0) or 1.0)
    K = _laplace_kappa.assemble(basis, kappa=basis.interpolate(kappa_nodal))
    M = (L ** 2) * _masse_ponderee.assemble(
        basis, rho_cp=basis.interpolate(rho_cp_nodal))
    b = (L ** 2) * _load.assemble(basis, f=basis.interpolate(source_nodal))



    K, b = _appliquer_robin(K, b, mesh, basis, field0.walls, echelle_bord=L)

    D = np.nonzero(fixed_nodal)[0]

    A = (M / dt + K).tolil()
    for k in D:
        A.rows[k] = [k]
        A.data[k] = [1.0]
    resoudre_pas = spla.factorized(A.tocsc())

    T = np.full(basis.N, float(T_initiale))
    T[D] = v_nodal[D]

    n_pas = max(1, int(round(duree / dt)))
    pas_par_image = max(1, n_pas // n_images)

    champs, instants = [], []
    t0 = perf_counter()
    for it in range(n_pas + 1):
        if it % pas_par_image == 0 or it == n_pas:
            V2d = _extraire_grille_base(T, basis.doflocs, n_base, field0.N)
            champ = Field(V2d, field0.fixed_mask.copy(), field0.solid_mask.copy(),
                          field0.h, dict(field0.walls), field0.omega, field0.source.copy(),
                          field0.kappa.copy(),
                          getattr(field0, "taille_domaine", 1.0),
                          field0.rho_cp.copy())
            champs.append(champ)
            instants.append(it * dt)
            if progress is not None:
                progress(it, 0.0)
        if it == n_pas:
            break
        verifier(annule)
        rhs = M.dot(T) / dt + b
        rhs[D] = v_nodal[D]
        T = resoudre_pas(rhs)

    temps_calcul = perf_counter() - t0
    return TransientResult(champs, instants, dt, temps_calcul, True, len(champs), 0.0)
