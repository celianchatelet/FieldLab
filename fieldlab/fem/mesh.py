import numpy as np
import skfem


def unit_square_mesh(n: int, refine: int = 0) -> skfem.MeshTri:
    if n < 2:
        raise ValueError("Le maillage doit avoir au moins 2 subdivisions par cote.")
    pts = np.linspace(0.0, 1.0, n + 1)
    mesh = skfem.MeshTri.init_tensor(pts, pts)
    return mesh.refined(refine) if refine > 0 else mesh
