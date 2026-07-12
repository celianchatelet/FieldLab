import numpy as np

from fieldlab.fem3d.scene_editor import centre_item, points_locaux
from fieldlab.materials import MATERIAUX, kappa_pour_domaine

AXES = ("x", "y", "z")


def construire_arguments(forme: str, cx: float, cy: float, cz: float,
                          rayon: float = 0.1, lx: float = 0.2,
                          ly: float = 0.2, lz: float = 0.2,
                          longueur: float = 1.0, axe: str = "z") -> dict:
    if forme == "sphere":
        if rayon <= 0:
            raise ValueError("Le rayon de la sphere doit etre strictement positif.")
        return {"cx": cx, "cy": cy, "cz": cz, "r": rayon}
    if forme == "boite":
        if min(lx, ly, lz) <= 0:
            raise ValueError("Les dimensions Lx, Ly et Lz doivent etre positives.")
        return {"x0": cx - lx / 2.0, "y0": cy - ly / 2.0,
                "z0": cz - lz / 2.0, "x1": cx + lx / 2.0,
                "y1": cy + ly / 2.0, "z1": cz + lz / 2.0}
    if forme == "cylindre":
        if rayon <= 0 or longueur <= 0:
            raise ValueError(
                "Le rayon et la longueur du cylindre doivent etre positifs.")
        if axe not in AXES:
            raise KeyError(f"Axe inconnu : {axe!r}. Choix : {AXES}")
        return {"cx": cx, "cy": cy, "cz": cz, "r": rayon,
                "longueur": longueur, "axe": axe}
    raise KeyError(
        f"Forme inconnue : {forme!r}. Choix : ('sphere', 'boite', 'cylindre')")


def _appliquer(field, masque: np.ndarray, bc) -> None:
    if bc[0] == "dirichlet":
        field.V[masque] = bc[1]
        field.fixed_mask[masque] = True
        field.solid_mask[masque] = False
    elif bc[0] == "isolant":
        field.solid_mask[masque] = True
        field.fixed_mask[masque] = False
        field.V[masque] = 0.0
    elif bc[0] == "source":
        field.source[masque] = bc[1]
    elif bc[0] == "materiau":
        field.kappa[masque] = bc[1]


        if len(bc) > 2 and bc[2] is not None \
                and getattr(field, "rho_cp", None) is not None:
            field.rho_cp[masque] = bc[2]
    else:
        raise ValueError(f"Condition inconnue : {bc!r}")


def sphere(field, cx: float, cy: float, cz: float, r: float, bc) -> None:
    x, y, z = field.basis.doflocs
    masque = (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= r ** 2
    _appliquer(field, masque, bc)


def boite(field, x0: float, y0: float, z0: float, x1: float, y1: float,
          z1: float, bc) -> None:
    x, y, z = field.basis.doflocs
    masque = ((x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
              & (z >= z0) & (z <= z1))
    _appliquer(field, masque, bc)


def cylindre(field, cx: float, cy: float, cz: float, r: float,
             longueur: float, bc, axe: str = "z") -> None:
    x, y, z = field.basis.doflocs
    if axe == "z":
        radial2, axial, c_axe = (x - cx) ** 2 + (y - cy) ** 2, z, cz
    elif axe == "x":
        radial2, axial, c_axe = (y - cy) ** 2 + (z - cz) ** 2, x, cx
    elif axe == "y":
        radial2, axial, c_axe = (x - cx) ** 2 + (z - cz) ** 2, y, cy
    else:
        raise KeyError(f"Axe inconnu : {axe!r}. Choix : {AXES}")
    masque = (radial2 <= r ** 2) & (np.abs(axial - c_axe) <= longueur / 2.0)
    _appliquer(field, masque, bc)


FORMES = {
    "sphere": sphere,
    "boite": boite,
    "cylindre": cylindre,
}


def appliquer_obstacles(field, obstacles) -> None:
    for o in obstacles or []:
        FORMES[o["forme"]](field, bc=o["bc"], **o["args"])


def masque_item(field, item) -> np.ndarray:
    points = field.basis.doflocs.T
    p = item.params
    centre = centre_item(item)
    locaux = points_locaux(points, centre, item.rotation)
    if item.forme == "sphere":
        return np.sum(locaux ** 2, axis=1) <= float(p["r"]) ** 2
    if item.forme == "boite":
        if all(nom in p for nom in ("lx", "ly", "lz")):
            demi = np.array([p["lx"], p["ly"], p["lz"]], dtype=float) / 2.0
        else:
            demi = np.array([
                p["x1"] - p["x0"], p["y1"] - p["y0"],
                p["z1"] - p["z0"]], dtype=float) / 2.0
        return np.all(np.abs(locaux) <= demi + 1e-12, axis=1)
    if item.forme == "cylindre":
        if np.allclose(item.rotation, 0.0) and p.get("axe", "z") != "z":
            axe = p["axe"]
            if axe == "x":
                radial2, axial = locaux[:, 1] ** 2 + locaux[:, 2] ** 2, locaux[:, 0]
            elif axe == "y":
                radial2, axial = locaux[:, 0] ** 2 + locaux[:, 2] ** 2, locaux[:, 1]
            else:
                raise KeyError(f"Axe inconnu : {axe!r}")
        else:
            radial2 = locaux[:, 0] ** 2 + locaux[:, 1] ** 2
            axial = locaux[:, 2]
        return ((radial2 <= float(p["r"]) ** 2)
                & (np.abs(axial) <= float(p["longueur"]) / 2.0))
    raise ValueError(
        f"La forme {item.forme!r} ne peut pas être appliquée au solveur 3D.")


def condition_item(item, domaine_nom: str):
    if item.role == "electrode":
        if item.valeur is None:
            raise ValueError(f"{item.label} exige une valeur imposée.")
        return ("dirichlet", float(item.valeur))
    if item.role == "isolant":
        return ("isolant",)
    if item.role in ("materiau", "conducteur"):
        nom = item.materiau or ("Cuivre" if item.role == "conducteur" else None)
        if nom not in MATERIAUX:
            raise ValueError(f"Matériau inconnu pour {item.label} : {nom!r}")
        materiau = MATERIAUX[nom]
        return ("materiau", kappa_pour_domaine(materiau, domaine_nom),
                materiau.rho_cp)
    if item.role == "source":
        valeur = item.q if item.q is not None else item.valeur
        if valeur is None:
            raise ValueError(f"{item.label} exige une source volumique q.")
        return ("source", float(valeur))
    if item.role == "decoratif":
        return None
    raise ValueError(f"Rôle de scène non applicable : {item.role!r}")


def appliquer_items_scene(field, scene, domaine_nom: str,
                          appliquer_ambiant=False) -> None:
    if domaine_nom == "Magnetostatique":
        raise ValueError(
            "Les solides magnétiques 3D exigeraient un potentiel-vecteur ; "
            "Seuls les circuits Biot–Savart sont appliqués en magnétisme.")
    if appliquer_ambiant:
        if scene.materiau_ambiant not in MATERIAUX:
            raise ValueError(
                f"Milieu ambiant inconnu : {scene.materiau_ambiant!r}")
        field.kappa[:] = kappa_pour_domaine(
            MATERIAUX[scene.materiau_ambiant], domaine_nom)
    for item in scene.items:
        bc = condition_item(item, domaine_nom)
        if bc is not None:
            if item.forme == "maillage_importe":
                raise ValueError(
                    f"{item.label} est un solide importé : son rôle physique "
                    "nodal exige une primitive analytique. Utilisez-le comme "
                    "domaine CAO ou objet décoratif.")
            _appliquer(field, masque_item(field, item), bc)
