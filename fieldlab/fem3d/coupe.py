import numpy as np


def origine_plan_dans_bornes(bornes, normale, fraction):
    normale = np.asarray(normale, dtype=float)
    norme = float(np.linalg.norm(normale))
    if norme <= 1e-14:
        raise ValueError("La normale d'un plan ne peut pas etre nulle.")
    normale /= norme
    fraction = float(fraction)
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("La position relative doit appartenir a [0, 1].")
    xmin, xmax, ymin, ymax, zmin, zmax = map(float, bornes)
    if xmin >= xmax or ymin >= ymax or zmin >= zmax:
        raise ValueError("Les bornes 3D sont invalides.")
    coins = np.array([
        [x, y, z]
        for x in (xmin, xmax)
        for y in (ymin, ymax)
        for z in (zmin, zmax)
    ])
    projections = coins @ normale
    cible = projections.min() + fraction * np.ptp(projections)
    centre = np.array([
        (xmin + xmax) / 2.0,
        (ymin + ymax) / 2.0,
        (zmin + zmax) / 2.0,
    ])
    return tuple(centre + (cible - centre @ normale) * normale)


def fractions_plans(position, nombre, ecart=0.18):
    position = float(position)
    nombre = int(nombre)
    if not 0.0 <= position <= 1.0:
        raise ValueError("La position centrale doit appartenir a [0, 1].")
    if not 1 <= nombre <= 3:
        raise ValueError("Le nombre de plans doit etre compris entre 1 et 3.")
    decalages = np.linspace(-ecart, ecart, nombre) if nombre > 1 else [0.0]
    return [min(1.0, max(0.0, position + float(d))) for d in decalages]
