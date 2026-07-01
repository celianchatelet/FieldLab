from dataclasses import dataclass
from time import perf_counter

import numpy as np

from fieldlab.grid import Field


def moyenne_voisins(V, fluid):
    up = V[:-2, 1:-1]; uo = fluid[:-2, 1:-1]
    dn = V[2:, 1:-1];  do = fluid[2:, 1:-1]
    lf = V[1:-1, :-2]; lo = fluid[1:-1, :-2]
    rt = V[1:-1, 2:];  ro = fluid[1:-1, 2:]

    num = up * uo + dn * do + lf * lo + rt * ro
    cnt = uo.astype(np.int16) + do + lo + ro
    cnt_safe = np.where(cnt == 0, 1, cnt)

    moy = np.zeros_like(V)
    moy[1:-1, 1:-1] = num / cnt_safe
    return moy


@dataclass
class SolverResult:
    champ: Field
    iterations: int
    erreur: float
    temps: float
    converge: bool
    historique: list


def solve(field, step_fn, tol=1e-5, max_iter=10000, progress=None):
    field = field.copy()
    t0 = perf_counter()
    err = float("inf")
    rel = float("inf")
    it = 0
    hist = []
    for it in range(1, max_iter + 1):
        err = step_fn(field)
        hist.append(err)
        # Tolerance RELATIVE : robuste a l'echelle (sources fortes, radiation...).
        denom = max(float(np.max(np.abs(field.V))), 1e-12)
        rel = err / denom
        if progress is not None and it % 25 == 0:
            progress(it, err)
        if rel < tol:
            break
    temps = perf_counter() - t0
    return SolverResult(field, it, err, temps, rel < tol, hist)
