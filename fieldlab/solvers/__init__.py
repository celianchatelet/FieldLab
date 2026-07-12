from fieldlab.solvers import base, jacobi, gauss_seidel, sor
from fieldlab.solvers.base import SolverResult as SolverResult







METHODES = ["Jacobi", "Gauss-Seidel", "SOR", "FEM (direct)", "FEM (CG)"]


def solve(field, methode, omega=None, tol=1e-5, max_iter=10000, progress=None,
          refine=0, annule=None):
    from fieldlab.annulation import verifier
    verifier(annule)
    if methode == "Jacobi":
        step = jacobi.step
    elif methode == "Gauss-Seidel":
        step = gauss_seidel.step
    elif methode == "SOR":
        w = omega if omega else sor.omega_optimal(field.N)
        step = sor.make_step(w)
    elif methode == "FEM (direct)":
        from fieldlab.fem.poisson import solve_poisson_from_field
        return solve_poisson_from_field(field, methode="direct", tol=tol,
                                         max_iter=max_iter, refine=refine,
                                         annule=annule)
    elif methode == "FEM (CG)":
        from fieldlab.fem.poisson import solve_poisson_from_field
        return solve_poisson_from_field(field, methode="cg", tol=tol, max_iter=max_iter,
                                         refine=refine, progress=progress,
                                         annule=annule)
    else:
        raise KeyError(f"Methode inconnue : {methode!r}. Choix : {METHODES}")
    return base.solve(field, step, tol=tol, max_iter=max_iter,
                      progress=progress, annule=annule)
