import numpy as np

from fieldlab.annulation import verifier
from fieldlab.constantes import MU_0


def champ_segments(points_fil: np.ndarray, courant: float,
                    points_eval: np.ndarray, annule=None) -> np.ndarray:
    pts = np.asarray(points_eval, dtype=float)
    fil = np.asarray(points_fil, dtype=float)
    verifier(annule)

    n_seg = fil.shape[0] - 1
    if pts.shape[0] * n_seg > 2_000_000:
        taille_bloc = max(1, 2_000_000 // n_seg)
        morceaux = []
        for i in range(0, pts.shape[0], taille_bloc):
            verifier(annule)
            morceaux.append(champ_segments(
                fil, courant, pts[i:i + taille_bloc], annule=annule))
        return np.vstack(morceaux)
    p1 = fil[:-1]
    p2 = fil[1:]
    u = p2 - p1


    r1 = pts[:, None, :] - p1[None, :, :]
    r2 = pts[:, None, :] - p2[None, :, :]

    croix = np.cross(np.broadcast_to(u, r1.shape), r1)
    croix2 = np.einsum("ijk,ijk->ij", croix, croix)
    n1 = np.linalg.norm(r1, axis=2)
    n2 = np.linalg.norm(r2, axis=2)

    with np.errstate(divide="ignore", invalid="ignore"):
        facteur = (np.einsum("jk,ijk->ij", u, r1) / n1
                   - np.einsum("jk,ijk->ij", u, r2) / n2) / croix2

    facteur = np.where(np.isfinite(facteur), facteur, 0.0)

    B = (MU_0 * courant / (4.0 * np.pi)) * np.einsum(
        "ij,ijk->ik", facteur, croix)
    return B


def fil_droit(p_debut, p_fin) -> np.ndarray:
    return np.array([p_debut, p_fin], dtype=float)


def spire(centre, rayon: float, axe: str = "z", n_segments: int = 72) -> np.ndarray:
    centre = np.asarray(centre, dtype=float)
    t = np.linspace(0.0, 2.0 * np.pi, n_segments + 1)
    c, s = rayon * np.cos(t), rayon * np.sin(t)
    zeros = np.zeros_like(t)
    if axe == "z":
        pts = np.column_stack([c, s, zeros])
    elif axe == "x":
        pts = np.column_stack([zeros, c, s])
    elif axe == "y":
        pts = np.column_stack([s, zeros, c])
    else:
        raise KeyError(f"Axe inconnu : {axe!r}")
    return centre + pts


def solenoide(centre, rayon: float, longueur: float, n_spires: int,
               axe: str = "z", n_segments: int = 48) -> np.ndarray:
    centre = np.asarray(centre, dtype=float)
    t = np.linspace(0.0, 2.0 * np.pi * n_spires, n_spires * n_segments + 1)
    c, s = rayon * np.cos(t), rayon * np.sin(t)
    h = np.linspace(-longueur / 2.0, longueur / 2.0, t.size)
    if axe == "z":
        pts = np.column_stack([c, s, h])
    elif axe == "x":
        pts = np.column_stack([h, c, s])
    elif axe == "y":
        pts = np.column_stack([s, h, c])
    else:
        raise KeyError(f"Axe inconnu : {axe!r}")
    return centre + pts


def helmholtz(centre, rayon: float, axe: str = "z",
               n_segments: int = 72) -> list:
    centre = np.asarray(centre, dtype=float)
    d = {"x": np.array([1.0, 0, 0]), "y": np.array([0, 1.0, 0]),
         "z": np.array([0, 0, 1.0])}[axe]
    return [spire(centre - d * rayon / 2.0, rayon, axe, n_segments),
            spire(centre + d * rayon / 2.0, rayon, axe, n_segments)]


def champ_total(circuits, courant: float, points_eval: np.ndarray,
                annule=None) -> np.ndarray:
    B = np.zeros((np.asarray(points_eval).shape[0], 3))
    for fil in circuits:
        verifier(annule)
        B += champ_segments(
            fil, courant, points_eval, annule=annule)
    return B
