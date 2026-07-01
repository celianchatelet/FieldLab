from fieldlab.solvers import base, jacobi, gauss_seidel, sor
from fieldlab.solvers.base import SolverResult

METHODES = ["Jacobi", "Gauss-Seidel", "SOR"]


def solve(field, methode, omega=None, tol=1e-5, max_iter=10000, progress=None):
    if methode == "Jacobi":
        step = jacobi.step
    elif methode == "Gauss-Seidel":
        step = gauss_seidel.step
    elif methode == "SOR":
        w = omega if omega else sor.omega_optimal(field.N)
        step = sor.make_step(w)
    else:
        raise KeyError(f"Methode inconnue : {methode!r}. Choix : {METHODES}")
    return base.solve(field, step, tol=tol, max_iter=max_iter, progress=progress)
