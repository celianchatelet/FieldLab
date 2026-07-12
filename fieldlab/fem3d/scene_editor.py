import copy

import numpy as np

from fieldlab import biot_savart as bs
from fieldlab.fem3d.scene import Circuit3D, ItemGeometrie


TYPES_CIRCUITS = ("fil", "spire", "solenoide", "helmholtz", "polyligne")


def matrice_rotation_euler(rotation):
    rx, ry, rz = np.radians(np.asarray(rotation, dtype=float))
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def points_locaux(points_monde, centre, rotation):
    points = np.asarray(points_monde, dtype=float)
    centre = np.asarray(centre, dtype=float)
    return (points - centre) @ matrice_rotation_euler(rotation)


def tourner_points(points_locaux_entree, centre, rotation):
    points = np.asarray(points_locaux_entree, dtype=float)
    return points @ matrice_rotation_euler(rotation).T + np.asarray(centre)


def angles_euler_depuis_matrice(matrice):
    m = np.asarray(matrice, dtype=float)
    if m.shape != (3, 3) or not np.all(np.isfinite(m)):
        raise ValueError("La matrice de rotation doit être une matrice 3×3 finie.")


    u, _s, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    cy = float(np.hypot(r[0, 0], r[1, 0]))
    if cy > 1e-10:
        rx = np.arctan2(r[2, 1], r[2, 2])
        ry = np.arctan2(-r[2, 0], cy)
        rz = np.arctan2(r[1, 0], r[0, 0])
    else:
        rx = np.arctan2(-r[1, 2], r[1, 1])
        ry = np.arctan2(-r[2, 0], cy)
        rz = 0.0
    return tuple(float(v) for v in np.degrees((rx, ry, rz)))


def coins_depuis_bornes(bornes):
    b = tuple(float(v) for v in bornes)
    return np.array([
        [x, y, z]
        for x in (b[0], b[1])
        for y in (b[2], b[3])
        for z in (b[4], b[5])
    ])


def contraindre_affine_dans_domaine(matrice, bornes_objet, bornes_domaine):
    m = np.asarray(matrice, dtype=float).copy()
    if m.shape != (4, 4):
        raise ValueError("Une transformation affine doit être une matrice 4×4.")
    coins = coins_depuis_bornes(bornes_objet)
    transformes = coins @ m[:3, :3].T + m[:3, 3]
    minimum = transformes.min(axis=0)
    maximum = transformes.max(axis=0)
    d = tuple(float(v) for v in bornes_domaine)
    dmin = np.array([d[0], d[2], d[4]])
    dmax = np.array([d[1], d[3], d[5]])
    correction = np.zeros(3)
    for axe in range(3):
        if maximum[axe] - minimum[axe] > dmax[axe] - dmin[axe]:
            correction[axe] = ((dmin[axe] + dmax[axe]) / 2.0
                               - (minimum[axe] + maximum[axe]) / 2.0)
        elif minimum[axe] < dmin[axe]:
            correction[axe] = dmin[axe] - minimum[axe]
        elif maximum[axe] > dmax[axe]:
            correction[axe] = dmax[axe] - maximum[axe]
    m[:3, 3] += correction
    return m


def transformer_element_affine(element, matrice):
    transforme = copy.deepcopy(element)
    m = np.asarray(matrice, dtype=float)
    a, t = m[:3, :3], m[:3, 3]
    if isinstance(transforme, ItemGeometrie):
        p = transforme.params
        if transforme.forme == "maillage_importe":
            ancien = np.asarray(p.get("decalage", (0.0, 0.0, 0.0)), float)
            p["decalage"] = (a @ ancien + t).tolist()
        else:
            centre = centre_item(transforme)
            nouveau = a @ centre + t
            if all(c in p for c in ("cx", "cy", "cz")):
                p.update(cx=float(nouveau[0]), cy=float(nouveau[1]),
                         cz=float(nouveau[2]))
            elif transforme.forme == "boite":
                delta = nouveau - centre
                for nom, valeur in zip(("x0", "y0", "z0"), delta):
                    p[nom] = float(p[nom] + valeur)
                for nom, valeur in zip(("x1", "y1", "z1"), delta):
                    p[nom] = float(p[nom] + valeur)
        rotation = a @ matrice_rotation_euler(transforme.rotation)
        transforme.rotation = angles_euler_depuis_matrice(rotation)
        return transforme
    if isinstance(transforme, Circuit3D):
        transforme.points = transforme.points @ a.T + t
        if "centre" in transforme.params:
            centre = np.asarray(transforme.params["centre"], dtype=float)
            transforme.params["centre"] = (a @ centre + t).tolist()
        rotation = a @ matrice_rotation_euler(
            transforme.params.get("rotation", (0.0, 0.0, 0.0)))
        transforme.params["rotation"] = list(
            angles_euler_depuis_matrice(rotation))
        return transforme
    raise TypeError("Élément de scène non transformable.")


def params_primitive(forme, centre, rayon=0.1, dimensions=(0.2, 0.2, 0.2),
                     longueur=0.5):
    cx, cy, cz = map(float, centre)
    if forme == "sphere":
        if rayon <= 0:
            raise ValueError("Le rayon doit être strictement positif.")
        return {"cx": cx, "cy": cy, "cz": cz, "r": float(rayon)}
    if forme == "boite":
        lx, ly, lz = map(float, dimensions)
        if min(lx, ly, lz) <= 0:
            raise ValueError("Les dimensions de boîte doivent être positives.")
        return {"cx": cx, "cy": cy, "cz": cz,
                "lx": lx, "ly": ly, "lz": lz}
    if forme == "cylindre":
        if rayon <= 0 or longueur <= 0:
            raise ValueError("Le rayon et la longueur doivent être positifs.")
        return {"cx": cx, "cy": cy, "cz": cz,
                "r": float(rayon), "longueur": float(longueur)}
    raise KeyError(f"Primitive inconnue : {forme!r}")


def centre_item(item: ItemGeometrie):
    p = item.params
    if all(c in p for c in ("cx", "cy", "cz")):
        return np.array([p["cx"], p["cy"], p["cz"]], dtype=float)
    if item.forme == "boite":
        return np.array([
            (p["x0"] + p["x1"]) / 2,
            (p["y0"] + p["y1"]) / 2,
            (p["z0"] + p["z1"]) / 2,
        ])
    raise ValueError("Le centre de cette géométrie n'est pas disponible.")


def circuits_depuis_parametres(type_circuit, centre, courant=5.0,
                               rayon=0.2, longueur=0.6, n_spires=12,
                               rotation=(0.0, 0.0, 0.0), points=None,
                               label=None):
    if type_circuit not in TYPES_CIRCUITS:
        raise KeyError(f"Type de circuit inconnu : {type_circuit!r}")
    centre = np.asarray(centre, dtype=float)
    label = label or type_circuit.capitalize()
    if type_circuit == "polyligne":
        pts = np.asarray(points, dtype=float)
        params = {"points": pts.tolist()}
        return [Circuit3D(
            pts, courant, type_circuit, label, params=params)]
    if type_circuit == "fil":
        locaux = np.array([[0.0, 0.0, -longueur / 2.0],
                           [0.0, 0.0, longueur / 2.0]])
        groupes = [locaux]
    elif type_circuit == "spire":
        groupes = [bs.spire([0, 0, 0], rayon, axe="z")]
    elif type_circuit == "solenoide":
        groupes = [bs.solenoide(
            [0, 0, 0], rayon, longueur, int(n_spires), axe="z")]
    else:
        groupes = bs.helmholtz([0, 0, 0], rayon, axe="z")
    params = {
        "centre": centre.tolist(), "rayon": float(rayon),
        "longueur": float(longueur), "n_spires": int(n_spires),
        "rotation": list(map(float, rotation)),
    }
    return [
        Circuit3D(
            tourner_points(groupe, centre, rotation), courant,
            type_circuit, label if len(groupes) == 1 else f"{label} {i + 1}",
            params=params)
        for i, groupe in enumerate(groupes)
    ]
