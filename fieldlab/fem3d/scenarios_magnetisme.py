from time import perf_counter

import numpy as np
import skfem

from fieldlab import biot_savart as bs
from fieldlab.annulation import verifier
from fieldlab.fem3d.field3d import Field3D
from fieldlab.fem3d.mesh import box_mesh, unit_cube_mesh
from fieldlab.fem3d.poisson import FemSolverResult3D
from fieldlab.fem3d.scene import Scene3D, scene_cube

_COURANT = 5.0


def resultat_depuis_scene(scene: Scene3D, n: int = 16, annule=None):
    t0 = perf_counter()
    mesh = box_mesh(n, scene.dimensions)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    points = basis.doflocs.T
    B = np.zeros((basis.N, 3))
    for circuit in scene.circuits:
        verifier(annule)
        B += bs.champ_segments(
            circuit.points, circuit.courant, points, annule=annule)
    champ = Field3D(
        mesh, basis, np.linalg.norm(B, axis=1),
        np.zeros(basis.N, dtype=bool), vecteurs=B,
        libelle_scalaire="|B| (T)", scene=scene)
    return FemSolverResult3D(
        champ, iterations=1, erreur=0.0,
        temps=perf_counter() - t0, converge=True, historique=[])


def environnement_vide_magnetique(n: int = 16,
                                   dimensions=(1.0, 1.0, 1.0),
                                   scene: Scene3D = None, annule=None,
                                   **_kwargs):
    if scene is None:
        dimensions = np.asarray(dimensions, dtype=float)
        scene = Scene3D(
            float(np.max(dimensions)),
            ((0.0, 0.0, 0.0), tuple(dimensions)),
            materiau_ambiant="Air")
    return resultat_depuis_scene(scene, n=n, annule=annule)


def _resultat_depuis_circuits(circuits, n: int, courant: float = _COURANT,
                              taille_m: float = 1.0, annule=None):
    t0 = perf_counter()
    mesh = unit_cube_mesh(n, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    pts = basis.doflocs.T
    B = bs.champ_total(
        circuits, courant, pts, annule=annule)
    champ = Field3D(mesh, basis, np.linalg.norm(B, axis=1),
                     np.zeros(basis.N, dtype=bool), vecteurs=B,
                     libelle_scalaire="|B| (T)",
                     scene=scene_cube(taille_m, circuits=circuits))
    return FemSolverResult3D(champ, iterations=1, erreur=0.0,
                              temps=perf_counter() - t0, converge=True,
                              historique=[])


def fil_rectiligne(n: int = 16, taille_m: float = 1.0, annule=None):
    c = taille_m / 2.0
    fil = bs.fil_droit(
        [c, c, -20.0 * taille_m], [c, c, 21.0 * taille_m])
    return _resultat_depuis_circuits(
        [fil], n, taille_m=taille_m, annule=annule)


def deux_fils_opposes(n: int = 16, taille_m: float = 1.0, annule=None):
    from fieldlab.fem3d.scene import Circuit3D
    c, bas, haut = taille_m / 2.0, -20.0 * taille_m, 21.0 * taille_m
    scene = scene_cube(taille_m, circuits=[
        Circuit3D(bs.fil_droit([0.35 * taille_m, c, bas],
                               [0.35 * taille_m, c, haut]),
                  courant=_COURANT, type_circuit="fil",
                  label="Fil aller (+I)"),
        Circuit3D(bs.fil_droit([0.65 * taille_m, c, bas],
                               [0.65 * taille_m, c, haut]),
                  courant=-_COURANT, type_circuit="fil",
                  label="Fil retour (−I)", couleur="#2563eb"),
    ])
    return resultat_depuis_scene(scene, n=n, annule=annule)


def spire_horizontale(n: int = 16, taille_m: float = 1.0, annule=None):
    c = taille_m / 2.0
    boucle = bs.spire([c, c, c], 0.25 * taille_m, axe="z")
    return _resultat_depuis_circuits(
        [boucle], n, taille_m=taille_m, annule=annule)


def bobines_helmholtz(n: int = 16, taille_m: float = 1.0, annule=None):
    c = taille_m / 2.0
    paire = bs.helmholtz([c, c, c], 0.25 * taille_m, axe="z")
    return _resultat_depuis_circuits(
        paire, n, taille_m=taille_m, annule=annule)


def solenoide_vertical(n: int = 16, taille_m: float = 1.0, annule=None):
    c = taille_m / 2.0
    sol = bs.solenoide(
        [c, c, c], 0.18 * taille_m, 0.6 * taille_m, n_spires=12,
        axe="z", n_segments=36)
    return _resultat_depuis_circuits(
        [sol], n, taille_m=taille_m, annule=annule)


SCENARIOS_3D_MAGNETISME = {
    "Scène libre (objets et parois personnalisés)": environnement_vide_magnetique,
    "Fil rectiligne (anneaux de B)": fil_rectiligne,
    "Deux fils (opposés)": deux_fils_opposes,
    "Spire (dipôle magnétique)": spire_horizontale,
    "Bobines de Helmholtz (champ uniforme)": bobines_helmholtz,
    "Solénoïde (12 spires)": solenoide_vertical,
}
