from time import perf_counter

import numpy as np

from fieldlab.annulation import verifier
from fieldlab import geometries as geo
from fieldlab.fem.poisson import FactorisationDirichlet, preparer_systeme, resoudre_systeme
from fieldlab.fem.transient import TransientResult
from fieldlab.solvers import solve
from fieldlab.sources import FORMES_TEMPORELLES

_METHODES_FEM_GUI = {"FEM (direct)": "direct", "FEM (CG)": "cg"}


def resoudre_regime_variable(scenarios, nom_scenario: str, N: int,
                              amplitude: float, forme: str, frequence: float,
                              walls: dict, obstacles: list, methode: str,
                              omega: float, tol: float, max_iter: int,
                              refine: int, duree: float, n_images: int,
                              kappa_fond: float = 1.0,
                              taille_domaine: float = 1.0,
                              facteur_source: float = 1.0,
                              progress=None, annule=None) -> TransientResult:
    if forme not in FORMES_TEMPORELLES:
        raise KeyError(f"Forme temporelle inconnue : {forme!r}. Choix : {list(FORMES_TEMPORELLES)}")
    if duree <= 0:
        raise ValueError("La duree simulee doit etre strictement positive.")

    forme_fn = FORMES_TEMPORELLES[forme]
    instants = np.linspace(0.0, duree, max(2, n_images + 1))

    methode_fem = _METHODES_FEM_GUI.get(methode)
    systeme = None
    cache = None

    champs = []
    convergence_globale = True
    t0 = perf_counter()
    for k, t in enumerate(instants):
        verifier(annule)
        val = float(forme_fn(t, amplitude, frequence))
        field = geo.build(scenarios, nom_scenario, N, val, walls, obstacles,
                           kappa_fond=kappa_fond,
                           taille_domaine=taille_domaine,
                           facteur_source=facteur_source)
        if methode_fem is not None:
            if systeme is None:
                systeme = preparer_systeme(field, refine=refine)
                if methode_fem == "direct":
                    cache = FactorisationDirichlet(systeme, field)
            res = resoudre_systeme(systeme, field, methode=methode_fem, tol=tol,
                                    max_iter=max_iter, cache=cache,
                                    annule=annule)
        else:
            res = solve(field, methode, omega=omega, tol=tol,
                        max_iter=max_iter, refine=refine, annule=annule)
        champs.append(res.champ)
        convergence_globale = convergence_globale and bool(res.converge)
        if progress is not None:
            progress(k + 1, 0.0)

    temps_calcul = perf_counter() - t0
    dt = float(instants[1] - instants[0]) if len(instants) > 1 else duree
    return TransientResult(champs, list(instants), dt, temps_calcul,
                            convergence_globale, len(champs))
