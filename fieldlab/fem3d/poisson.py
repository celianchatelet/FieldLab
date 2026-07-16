from dataclasses import dataclass
from time import perf_counter

import numpy as np
import scipy.sparse.linalg as spla
import skfem

from fieldlab.fem.poisson import (
    _KELVIN_0C, _STEFAN_BOLTZMANN, _laplace_kappa, _load, _robin_bord,
    _robin_source_bord, residu_relatif,
)
from fieldlab.annulation import verifier
from fieldlab.fem3d.field3d import Field3D
from fieldlab.fem3d.mesh import facettes_face

METHODES_FEM3D = ("direct", "cg")
_KAPPA_ISOLANT = 1e-6


def _appliquer_robin(K, b, mesh, basis, walls):
    for face, spec in (walls or {}).items():
        if spec[0] not in ("robin", "radiation", "flux"):
            continue
        facettes = facettes_face(mesh, face)
        if len(facettes) == 0:
            continue
        fb = skfem.FacetBasis(mesh, basis.elem, facets=facettes)
        if spec[0] == "flux":
            q = float(spec[1])
            b = b + q * _robin_source_bord.assemble(fb)
            continue
        if spec[0] == "robin":
            h_coef, v_inf = float(spec[1]), float(spec[2])
        else:
            epsilon, v_inf = float(spec[1]), float(spec[2])
            t_inf_k = v_inf + _KELVIN_0C
            h_coef = 4.0 * epsilon * _STEFAN_BOLTZMANN * t_inf_k ** 3
        K = K + h_coef * _robin_bord.assemble(fb)
        b = b + h_coef * v_inf * _robin_source_bord.assemble(fb)
    return K, b


@dataclass
class FemSolverResult3D:
    champ: Field3D
    iterations: int
    erreur: float
    temps: float
    converge: bool
    historique: list


@dataclass
class SystemeFEM3D:
    mesh: object
    basis: object
    K: object
    b: object


def preparer_systeme_3d(field: Field3D) -> SystemeFEM3D:
    mesh, basis = field.mesh, field.basis
    kappa_nodal = np.where(field.solid_mask, _KAPPA_ISOLANT, field.kappa)
    K = _laplace_kappa.assemble(basis, kappa=basis.interpolate(kappa_nodal))
    source_equation = field.source * float(
        getattr(field, "facteur_source", 1.0))
    b = _load.assemble(basis, f=basis.interpolate(source_equation))
    K, b = _appliquer_robin(K, b, mesh, basis, field.walls)
    return SystemeFEM3D(mesh, basis, K, b)


class FactorisationDirichlet:
    def __init__(self, systeme: SystemeFEM3D, D: np.ndarray):
        self.systeme = systeme
        self.D = D
        x0_nul = np.zeros(systeme.basis.N)
        K_enf, _ = skfem.enforce(systeme.K, systeme.b, x=x0_nul, D=D)
        self._resoudre_factorise = spla.factorized(K_enf.tocsc())

    def resoudre(self, x0: np.ndarray) -> np.ndarray:
        _, b_enf = skfem.enforce(self.systeme.K, self.systeme.b, x=x0, D=self.D)
        return self._resoudre_factorise(b_enf)


def resoudre_systeme_3d(systeme: SystemeFEM3D, field: Field3D, methode: str = "direct",
                         tol: float = 1e-8, max_iter: int = 10000, progress=None,
                         cache: FactorisationDirichlet = None,
                         annule=None) -> FemSolverResult3D:
    if methode not in METHODES_FEM3D:
        raise KeyError(f"Methode FEM 3D inconnue : {methode!r}. Choix : {METHODES_FEM3D}")

    verifier(annule)
    mesh, basis, K, b = systeme.mesh, systeme.basis, systeme.K, systeme.b
    D = np.nonzero(field.fixed_mask)[0]
    x0 = np.zeros(basis.N)
    x0[D] = field.V[D]

    t0 = perf_counter()
    if methode == "direct":
        u = cache.resoudre(x0) if cache is not None else skfem.solve(*skfem.enforce(K, b, x=x0, D=D))
        iterations = 1
        solveur_ok = True
    else:
        Kc, bc, _x0c, I = skfem.condense(K, b, x=x0, D=D)
        compteur = {"n": 0}

        def _compter(_xk, compteur=compteur):
            compteur["n"] += 1
            if progress is not None:
                progress(compteur["n"], 0.0)

        u_free, info = spla.cg(Kc, bc, rtol=tol, maxiter=max_iter, callback=_compter)
        u = x0.copy()
        u[I] = u_free
        iterations = compteur["n"]
        solveur_ok = (info == 0)

    libres = np.ones(basis.N, dtype=bool)
    libres[D] = False
    verifier(annule)
    erreur = residu_relatif(K, b, u, libres)
    fini = bool(np.all(np.isfinite(u)))
    converge = fini and solveur_ok and erreur <= tol
    if not fini:
        raise ValueError(
            "Le solveur 3D a produit des valeurs non finies. Le système est "
            "probablement singulier ou numériquement mal conditionné.")
    if progress is not None:
        progress(iterations, erreur)
    temps = perf_counter() - t0

    champ = Field3D(mesh, basis, u, field.fixed_mask.copy(), field.solid_mask.copy(),
                     dict(field.walls), field.source.copy(), field.kappa.copy(),
                     vecteurs=(None if field.vecteurs is None
                               else field.vecteurs.copy()),
                     libelle_scalaire=field.libelle_scalaire,
                     scene=field.scene, rho_cp=field.rho_cp.copy(),
                     facteur_source=field.facteur_source)
    return FemSolverResult3D(champ, iterations, erreur, temps, converge, [])


def solve_poisson_3d(field: Field3D, methode: str = "direct", tol: float = 1e-8,
                      max_iter: int = 10000, progress=None,
                      annule=None) -> FemSolverResult3D:
    verifier(annule)
    systeme = preparer_systeme_3d(field)
    verifier(annule)
    return resoudre_systeme_3d(systeme, field, methode=methode, tol=tol,
                                max_iter=max_iter, progress=progress,
                                annule=annule)
