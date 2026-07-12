from dataclasses import dataclass, field as dataclass_field, replace

import numpy as np

MODES_GRAINES = ("Automatique", "Volume", "Plan", "Surface", "Ligne")


@dataclass
class CalquesRendu3D:
    carte_scalaire: bool = True
    volume: bool = False
    iso_surfaces: bool = False
    lignes_champ: bool = False
    fleches: bool = False
    maillage: bool = False
    objets_scene: bool = True
    coupe: bool = False

    def copy(self):
        return replace(self)

    def aucun_calque_champ(self):
        return not (self.carte_scalaire or self.volume or self.iso_surfaces
                    or self.lignes_champ or self.fleches or self.coupe)





_PREREGLAGES = {
    "Carte scalaire": {"carte_scalaire": True},
    "Volume": {"carte_scalaire": True},
    "Iso-valeurs": {"iso_surfaces": True},
    "Champ (flèches)": {"fleches": True},
    "Lignes de champ": {"lignes_champ": True},
    "Intensité du champ": {"carte_scalaire": True},
    "Plan de coupe": {"carte_scalaire": True, "coupe": True},
}


def calques_depuis_mode(kind: str) -> CalquesRendu3D:
    reglage = _PREREGLAGES.get(kind)
    if reglage is None:
        reglage = _PREREGLAGES["Carte scalaire"]
    base = {"carte_scalaire": False, "volume": False, "iso_surfaces": False,
            "lignes_champ": False, "fleches": False, "maillage": False,
            "objets_scene": True, "coupe": False}
    base.update(reglage)
    return CalquesRendu3D(**base)


@dataclass
class OptionsGraines3D:
    mode: str = "Automatique"
    densite: int = 5
    marge: float = 0.06
    jitter: float = 0.35
    max_graines: int = 200
    seuil_champ: float = 0.02
    graine_aleatoire: int = 0
    afficher_graines: bool = False


def points_graines_volumiques(bounds, densite=5, marge=0.06, jitter=0.35,
                              graine_aleatoire=0) -> np.ndarray:
    densite = max(2, int(densite))
    marge = float(min(max(marge, 0.0), 0.45))
    xmin, xmax, ymin, ymax, zmin, zmax = (float(v) for v in bounds)
    etendues = np.array([xmax - xmin, ymax - ymin, zmax - zmin])
    if np.any(etendues <= 0):
        raise ValueError("Bornes 3D invalides pour l'ensemencement.")
    bas = np.array([xmin, ymin, zmin]) + marge * etendues
    haut = np.array([xmax, ymax, zmax]) - marge * etendues
    axes = [np.linspace(bas[i], haut[i], densite) for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    if jitter > 0 and densite > 1:
        pas = (haut - bas) / (densite - 1)
        rng = np.random.default_rng(int(graine_aleatoire))
        points = points + rng.uniform(-0.5, 0.5, points.shape) \
            * (float(jitter) * pas)
        points = np.clip(points, bas, haut)
    return points


def points_graines_ligne(bounds, densite=5, marge=0.06, axe=2) -> np.ndarray:
    densite = max(2, int(densite))
    xmin, xmax, ymin, ymax, zmin, zmax = (float(v) for v in bounds)
    bas = np.array([xmin, ymin, zmin])
    haut = np.array([xmax, ymax, zmax])
    centre = (bas + haut) / 2.0
    etendue = haut - bas
    n = max(3, densite * densite)
    points = np.tile(centre, (n, 1))
    points[:, axe] = np.linspace(
        bas[axe] + marge * etendue[axe],
        haut[axe] - marge * etendue[axe], n)
    return points


def sous_echantillonner(points: np.ndarray, maximum: int) -> np.ndarray:
    maximum = max(1, int(maximum))
    n = len(points)
    if n <= maximum:
        return points
    indices = np.unique(np.round(np.linspace(0, n - 1, maximum)).astype(int))
    return points[indices]
