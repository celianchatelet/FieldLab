from dataclasses import dataclass, field
from time import perf_counter

import numpy as np
import scipy.sparse.linalg as spla
import skfem

from fieldlab.annulation import verifier
from fieldlab.fem.poisson import _laplace_kappa, _load
from fieldlab.fem.transient import _masse_ponderee
from fieldlab.fem3d.field3d import Field3D
from fieldlab.fem3d.poisson import _appliquer_robin, _KAPPA_ISOLANT


@dataclass
class TransientResult3D:
    champs: list
    instants: list
    dt: float
    temps: float = 0.0
    converge: bool = True
    iterations: int = 0
    erreur: float = 0.0
    historique: list = field(default_factory=list)

    @property
    def champ(self) -> Field3D:
        return self.champs[-1]


def resoudre_transitoire_3d(field0: Field3D, T_initiale: float, dt: float,
                             duree: float, n_images: int = 60,
                             progress=None, annule=None) -> TransientResult3D:
    if dt <= 0:
        raise ValueError("Le pas de temps doit etre strictement positif.")
    if duree <= 0:
        raise ValueError("La duree simulee doit etre strictement positive.")
    if n_images < 1:
        raise ValueError("Le nombre d'images doit etre au moins 1.")

    mesh, basis = field0.mesh, field0.basis
    kappa_nodal = np.where(field0.solid_mask, _KAPPA_ISOLANT, field0.kappa)
    K = _laplace_kappa.assemble(basis, kappa=basis.interpolate(kappa_nodal))


    rho_cp_nodal = getattr(field0, "rho_cp", None)
    if rho_cp_nodal is None:
        rho_cp_nodal = np.ones(basis.N)
    M = _masse_ponderee.assemble(
        basis, rho_cp=basis.interpolate(rho_cp_nodal))
    source_equation = field0.source * float(
        getattr(field0, "facteur_source", 1.0))
    b = _load.assemble(basis, f=basis.interpolate(source_equation))
    K, b = _appliquer_robin(K, b, mesh, basis, field0.walls)

    D = np.nonzero(field0.fixed_mask)[0]
    v_nodal = field0.V

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
            champ = Field3D(mesh, basis, T.copy(), field0.fixed_mask.copy(),
                             field0.solid_mask.copy(), dict(field0.walls),
                             field0.source.copy(), field0.kappa.copy(),
                             scene=field0.scene,
                             rho_cp=field0.rho_cp.copy(),
                             facteur_source=field0.facteur_source)
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
    return TransientResult3D(champs, instants, dt, temps_calcul, True, len(champs), 0.0)
