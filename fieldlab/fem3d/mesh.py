import numpy as np
import skfem

FACES = ("gauche", "droite", "avant", "arriere", "bas", "haut")


def unit_cube_mesh(n: int, refine: int = 0,
                   taille_m: float = 1.0) -> skfem.MeshTet:
    taille_m = float(taille_m)
    if not np.isfinite(taille_m) or taille_m <= 0:
        raise ValueError("La taille physique 3D doit etre strictement positive.")
    return box_mesh(n, (taille_m, taille_m, taille_m), refine=refine)


def box_mesh(n: int, dimensions, refine: int = 0) -> skfem.MeshTet:
    if n < 2:
        raise ValueError("Le maillage doit avoir au moins 2 subdivisions par arete.")
    dimensions = np.asarray(dimensions, dtype=float)
    if dimensions.shape != (3,) or not np.all(np.isfinite(dimensions)) \
            or np.any(dimensions <= 0):
        raise ValueError("Lx, Ly et Lz doivent être trois longueurs positives.")
    x = np.linspace(0.0, dimensions[0], n + 1)
    y = np.linspace(0.0, dimensions[1], n + 1)
    z = np.linspace(0.0, dimensions[2], n + 1)
    mesh = skfem.MeshTet.init_tensor(x, y, z)
    return mesh.refined(refine) if refine > 0 else mesh


def facettes_face(mesh: skfem.MeshTet, face: str) -> np.ndarray:
    bf = mesh.boundary_facets()
    coords = mesh.p[:, mesh.facets[:, bf]]
    milieux = coords.mean(axis=1)
    minimum = mesh.p.min(axis=1)
    maximum = mesh.p.max(axis=1)
    if face == "gauche":
        return bf[np.isclose(milieux[0], minimum[0])]
    if face == "droite":
        return bf[np.isclose(milieux[0], maximum[0])]
    if face == "avant":
        return bf[np.isclose(milieux[1], minimum[1])]
    if face == "arriere":
        return bf[np.isclose(milieux[1], maximum[1])]
    if face == "bas":
        return bf[np.isclose(milieux[2], minimum[2])]
    if face == "haut":
        return bf[np.isclose(milieux[2], maximum[2])]
    raise KeyError(f"Face inconnue : {face!r}. Choix : {FACES}")
