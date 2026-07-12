import numpy as np


COURBES_OPACITE = ("Linéaire", "Sigmoïde", "Géométrique")


def courbe_opacite(nom, gain=1.0, n=256):
    if nom not in COURBES_OPACITE:
        raise KeyError(f"Courbe d'opacité inconnue : {nom!r}")
    gain = float(gain)
    n = int(n)
    if not 0.0 <= gain <= 1.0:
        raise ValueError("Le gain d'opacité doit appartenir à [0, 1].")
    if n < 2:
        raise ValueError("La courbe d'opacité exige au moins deux points.")
    x = np.linspace(0.0, 1.0, n)
    if nom == "Linéaire":
        forme = x
    elif nom == "Géométrique":
        forme = x ** 2.5
    else:
        forme = 1.0 / (1.0 + np.exp(-12.0 * (x - 0.55)))
        forme = (forme - forme[0]) / (forme[-1] - forme[0])
    return gain * forme


def niveaux_isosurfaces(valeurs, nombre, fraction_min=0.05,
                        fraction_max=0.95):
    valeurs = np.asarray(valeurs, dtype=float)
    nombre = int(nombre)
    fraction_min = float(fraction_min)
    fraction_max = float(fraction_max)
    if valeurs.size == 0 or not np.all(np.isfinite(valeurs)):
        raise ValueError("Les valeurs d'iso-surfaces doivent être finies.")
    if not 1 <= nombre <= 50:
        raise ValueError("Le nombre d'iso-surfaces doit être compris entre 1 et 50.")
    if not 0.0 <= fraction_min < fraction_max <= 1.0:
        raise ValueError("La plage relative des iso-surfaces est invalide.")
    minimum, maximum = float(np.min(valeurs)), float(np.max(valeurs))
    if np.isclose(minimum, maximum):
        return np.empty(0)
    debut = minimum + fraction_min * (maximum - minimum)
    fin = minimum + fraction_max * (maximum - minimum)
    return np.linspace(debut, fin, nombre)


def niveaux_isosurfaces_geometriques(minimum, maximum, nombre,
                                     fraction_min=0.05, fraction_max=0.95):
    minimum = float(minimum)
    maximum = float(maximum)
    nombre = int(nombre)
    if not 0.0 < minimum < maximum:
        raise ValueError(
            "Les bornes geometriques exigent 0 < minimum < maximum.")
    if not 1 <= nombre <= 50:
        raise ValueError("Le nombre d'iso-surfaces doit être compris entre 1 et 50.")
    if not 0.0 <= fraction_min < fraction_max <= 1.0:
        raise ValueError("La plage relative des iso-surfaces est invalide.")
    log_min, log_max = np.log10(minimum), np.log10(maximum)
    debut = log_min + float(fraction_min) * (log_max - log_min)
    fin = log_min + float(fraction_max) * (log_max - log_min)
    return 10.0 ** np.linspace(debut, fin, nombre)


def superpositions_coupe_par_defaut(kind):
    if kind == "Lignes de champ":
        return (False, False, True)
    if kind == "Champ (flèches)":
        return (False, True, False)
    return (True, False, False)


def abscisses_cumulees(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0:
        raise ValueError("Un profil doit contenir des points 3D.")
    if len(points) == 1:
        return np.zeros(1)
    pas = np.linalg.norm(np.diff(points, axis=0), axis=1)
    return np.concatenate(([0.0], np.cumsum(pas)))
