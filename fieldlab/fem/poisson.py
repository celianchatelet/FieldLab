from dataclasses import dataclass
from time import perf_counter

import numpy as np
import scipy.sparse.linalg as spla
import skfem

from fieldlab.annulation import verifier
from skfem.helpers import dot, grad

from fieldlab.fem.mesh import unit_square_mesh
from fieldlab.grid import Field

METHODES_FEM = ("direct", "cg")
_KAPPA_ISOLANT = 1e-6


@skfem.BilinearForm
def _laplace_kappa(u, v, w):
    return w["kappa"] * dot(grad(u), grad(v))


@skfem.LinearForm
def _load(v, w):
    return w["f"] * v


@skfem.BilinearForm
def _robin_bord(u, v, w):
    return u * v


@skfem.LinearForm
def _robin_source_bord(v, w):
    return v


_STEFAN_BOLTZMANN = 5.670374419e-8
_KELVIN_0C = 273.15


def _facettes_cote(mesh, cote: str) -> np.ndarray:
    bf = mesh.boundary_facets()
    coords = mesh.p[:, mesh.facets[:, bf]]
    milieux = coords.mean(axis=1)
    if cote == "gauche":
        return bf[np.isclose(milieux[0], 0.0)]
    if cote == "droite":
        return bf[np.isclose(milieux[0], 1.0)]
    if cote == "bas":
        return bf[np.isclose(milieux[1], 0.0)]
    if cote == "haut":
        return bf[np.isclose(milieux[1], 1.0)]
    raise KeyError(f"Cote inconnu : {cote!r}")


def _appliquer_robin(K, b, mesh, basis, walls, echelle_bord: float = 1.0):
    for cote, spec in (walls or {}).items():
        if spec[0] not in ("robin", "radiation", "flux"):
            continue
        facettes = _facettes_cote(mesh, cote)
        if len(facettes) == 0:
            continue
        fb = skfem.FacetBasis(mesh, basis.elem, facets=facettes)
        if spec[0] == "flux":
            q = float(spec[1])
            b = b + echelle_bord * q * _robin_source_bord.assemble(fb)
            continue
        if spec[0] == "robin":
            h_coef, v_inf = float(spec[1]), float(spec[2])
        else:
            epsilon, v_inf = float(spec[1]), float(spec[2])
            t_inf_k = v_inf + _KELVIN_0C
            h_coef = 4.0 * epsilon * _STEFAN_BOLTZMANN * t_inf_k ** 3
        K = K + echelle_bord * h_coef * _robin_bord.assemble(fb)
        b = b + echelle_bord * h_coef * v_inf * _robin_source_bord.assemble(fb)
    return K, b


@dataclass
class FemSolverResult:
    champ: Field
    iterations: int
    erreur: float
    temps: float
    converge: bool
    historique: list


def _resample_field_on_mesh(field: Field, n_base: int, doflocs: np.ndarray):
    N = field.N
    xs, ys = doflocs[0], doflocs[1]
    j = np.clip(np.round(xs * n_base).astype(int), 0, N - 1)
    i = np.clip(np.round(ys * n_base).astype(int), 0, N - 1)
    return (field.fixed_mask[i, j], field.V[i, j], field.solid_mask[i, j],
            field.source[i, j], field.kappa[i, j], i, j)


def _extraire_grille_base(u: np.ndarray, doflocs: np.ndarray, n_base: int, N: int):
    xs, ys = doflocs[0] * n_base, doflocs[1] * n_base
    sur_grille = np.isclose(xs, np.round(xs)) & np.isclose(ys, np.round(ys))
    j = np.round(xs[sur_grille]).astype(int)
    i = np.round(ys[sur_grille]).astype(int)
    V2d = np.zeros((N, N))
    V2d[i, j] = u[sur_grille]
    return V2d


def _ancrer_systeme_neumann(D: np.ndarray, b, walls: dict) -> np.ndarray:
    if D.size > 0:
        return D
    if any(spec and spec[0] in ("robin", "radiation")
           for spec in (walls or {}).values()):
        return D
    b = np.asarray(b).ravel()
    if abs(float(b.sum())) > 1e-9 * max(float(np.abs(b).sum()), 1e-30):
        raise ValueError(
            "Parois toutes en Neumann avec une source nette non nulle : le "
            "probleme n'a pas de solution (le courant/flux injecte doit se "
            "refermer). Ajoutez une source de signe oppose (courant de "
            "retour) ou repassez au moins une paroi en Dirichlet (A=0).")
    return np.array([0], dtype=int)


@dataclass
class SystemeFEM:
    mesh: object
    basis: object
    K: object
    b: object
    n_base: int


def preparer_systeme(field: Field, refine: int = 0) -> SystemeFEM:
    n_base = field.N - 1
    mesh = unit_square_mesh(n_base, refine=refine)
    basis = skfem.Basis(mesh, skfem.ElementTriP1())

    _fixed, _v, solid_nodal, source_nodal, kappa_materiau_nodal, _i, _j = \
        _resample_field_on_mesh(field, n_base, basis.doflocs)






    kappa_nodal = np.where(solid_nodal, _KAPPA_ISOLANT, kappa_materiau_nodal)











    L = float(getattr(field, "taille_domaine", 1.0) or 1.0)
    K = _laplace_kappa.assemble(basis, kappa=basis.interpolate(kappa_nodal))
    b = (L ** 2) * _load.assemble(basis, f=basis.interpolate(source_nodal))
    K, b = _appliquer_robin(K, b, mesh, basis, field.walls, echelle_bord=L)
    return SystemeFEM(mesh, basis, K, b, n_base)


class FactorisationDirichlet:
    def __init__(self, systeme: SystemeFEM, field: Field):
        self.systeme = systeme
        fixed_nodal, _v, _sm, _sn, _kn, _i, _j = _resample_field_on_mesh(
            field, systeme.n_base, systeme.basis.doflocs)
        self.D = _ancrer_systeme_neumann(
            np.nonzero(fixed_nodal)[0], systeme.b, field.walls)
        x0_nul = np.zeros(systeme.basis.N)
        K_enf, _ = skfem.enforce(systeme.K, systeme.b, x=x0_nul, D=self.D)
        self._resoudre_factorise = spla.factorized(K_enf.tocsc())

    def resoudre(self, x0: np.ndarray) -> np.ndarray:
        _, b_enf = skfem.enforce(self.systeme.K, self.systeme.b, x=x0, D=self.D)
        return self._resoudre_factorise(b_enf)


def residu_relatif(K, b, u, libres) -> float:
    libres = np.asarray(libres, dtype=bool)
    if not np.any(libres):
        return 0.0
    if not np.all(np.isfinite(u)):
        return float("inf")
    r = np.asarray(K @ u - b)[libres]
    if not np.all(np.isfinite(r)):
        return float("inf")
    echelle_lhs = np.asarray(abs(K[libres]) @ np.abs(u)).ravel()
    echelle_rhs = np.abs(np.asarray(b)[libres])
    echelle = max(
        float(np.max(echelle_lhs, initial=0.0)),
        float(np.max(echelle_rhs, initial=0.0)),
        np.finfo(float).eps,
    )
    return float(np.max(np.abs(r), initial=0.0) / echelle)


def resoudre_systeme(systeme: SystemeFEM, field: Field, methode: str = "direct",
                      tol: float = 1e-8, max_iter: int = 10000,
                      progress=None, cache: FactorisationDirichlet = None,
                      annule=None) -> FemSolverResult:
    if methode not in METHODES_FEM:
        raise KeyError(f"Methode FEM inconnue : {methode!r}. Choix : {METHODES_FEM}")

    verifier(annule)
    mesh, basis, K, b, n_base = (systeme.mesh, systeme.basis, systeme.K,
                                  systeme.b, systeme.n_base)
    fixed_nodal, v_nodal, _sm, _sn, _kn, _i_idx, _j_idx = \
        _resample_field_on_mesh(field, n_base, basis.doflocs)

    t0 = perf_counter()
    D = _ancrer_systeme_neumann(
        np.nonzero(fixed_nodal)[0], b, field.walls)
    x0 = np.zeros(basis.N)
    x0[D] = v_nodal[D]

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
            "Le solveur a produit des valeurs non finies. Le système est "
            "probablement singulier ou numériquement mal conditionné.")
    if progress is not None:
        progress(iterations, erreur)
    temps = perf_counter() - t0

    V2d = _extraire_grille_base(u, basis.doflocs, n_base, field.N)
    champ = Field(V2d, field.fixed_mask.copy(), field.solid_mask.copy(),
                  field.h, dict(field.walls), field.omega, field.source.copy(),
                  field.kappa.copy(),
                  getattr(field, "taille_domaine", 1.0),
                  field.rho_cp.copy())

    return FemSolverResult(champ, iterations, erreur, temps, converge, [])


def solve_poisson_from_field(field: Field, methode: str = "direct",
                              tol: float = 1e-8, max_iter: int = 10000,
                              refine: int = 0, progress=None,
                              annule=None) -> FemSolverResult:
    verifier(annule)
    systeme = preparer_systeme(field, refine=refine)
    verifier(annule)
    return resoudre_systeme(systeme, field, methode=methode, tol=tol,
                             max_iter=max_iter, progress=progress,
                             annule=annule)
