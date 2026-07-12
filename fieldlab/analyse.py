from __future__ import annotations

import numpy as np


def _integration_tetraedres(champ):
    p = np.asarray(champ.mesh.p, dtype=float)
    t = np.asarray(champ.mesh.t, dtype=int)
    a, b, c, d = (p[:, t[i]].T for i in range(4))
    volumes = np.abs(np.einsum(
        "ij,ij->i", b - a, np.cross(c - a, d - a))) / 6.0
    valeurs = np.asarray(champ.V, dtype=float)[t].mean(axis=0)
    return float(volumes.sum()), float(np.sum(volumes * valeurs))


def resumer_champ(champ, domaine) -> dict:
    valeurs = np.asarray(champ.V, dtype=float)
    finis = valeurs[np.isfinite(valeurs)]
    if finis.size == 0:
        raise ValueError("Le champ ne contient aucune valeur finie.")
    resume = {
        "minimum": float(finis.min()),
        "maximum": float(finis.max()),
        "moyenne_nodale": float(finis.mean()),
        "ecart_type": float(finis.std()),
    }
    if valeurs.ndim == 2:
        aire = float(getattr(champ, "taille_domaine", 1.0)) ** 2
        resume["mesure_domaine_m2"] = aire
        resume["integrale_scalaire"] = float(
            np.trapezoid(np.trapezoid(valeurs, dx=champ.h, axis=1),
                         dx=champ.h, axis=0))
        vx, vy, norme = domaine.champ_fn(champ)
        resume["champ_norme_max"] = float(np.nanmax(norme))
        resume["champ_norme_moyenne"] = float(np.nanmean(norme))

        resume["flux_sortant"] = float(
            np.trapezoid(-np.asarray(vy)[0, :], dx=champ.h)
            + np.trapezoid(np.asarray(vy)[-1, :], dx=champ.h)
            + np.trapezoid(-np.asarray(vx)[:, 0], dx=champ.h)
            + np.trapezoid(np.asarray(vx)[:, -1], dx=champ.h))
    else:
        volume, integrale = _integration_tetraedres(champ)
        resume["mesure_domaine_m3"] = volume
        resume["integrale_scalaire"] = integrale
        if getattr(champ, "vecteurs", None) is not None:
            normes = np.linalg.norm(champ.vecteurs, axis=1)
            resume["champ_norme_max"] = float(np.nanmax(normes))
            resume["champ_norme_moyenne"] = float(np.nanmean(normes))
    return resume


def comparer_champs(reference, courant) -> dict:
    a = np.asarray(reference.V, dtype=float)
    b = np.asarray(courant.V, dtype=float)
    if a.shape != b.shape:
        raise ValueError(
            "Les deux résultats n'ont pas la même discrétisation.")
    if hasattr(reference, "mesh") and hasattr(courant, "mesh") \
            and not np.allclose(reference.mesh.p, courant.mesh.p):
        raise ValueError("Les deux résultats 3D n'utilisent pas le même maillage.")
    difference = b - a
    echelle = max(float(np.nanmax(np.abs(a))), np.finfo(float).eps)
    return {
        "ecart_max": float(np.nanmax(np.abs(difference))),
        "rmse": float(np.sqrt(np.nanmean(difference ** 2))),
        "ecart_relatif_max": float(np.nanmax(np.abs(difference)) / echelle),
        "moyenne_difference": float(np.nanmean(difference)),
    }
