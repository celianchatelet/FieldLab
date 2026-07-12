import copy
import json
from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np


FORMES_SCENE = ("boite", "sphere", "cylindre", "maillage_importe")
OPERATIONS_CAO = ("aucune", "domaine", "union", "difference", "intersection")
ROLES_SCENE = (
    "electrode", "isolant", "materiau", "source", "conducteur",
    "decoratif",
)

COULEURS_ROLES = {
    "electrode": "#dc2626",
    "isolant": "#94a3b8",
    "materiau": "#16a34a",
    "source": "#f59e0b",
    "conducteur": "#b45309",
    "decoratif": "#7c3aed",
}


def _identifiant() -> str:
    return uuid4().hex


def _json_compatible(objet):
    if isinstance(objet, np.ndarray):
        return objet.tolist()
    if isinstance(objet, np.generic):
        return objet.item()
    if isinstance(objet, dict):
        return {str(k): _json_compatible(v) for k, v in objet.items()}
    if isinstance(objet, (list, tuple)):
        return [_json_compatible(v) for v in objet]
    return objet


@dataclass
class ItemGeometrie:
    forme: str
    params: dict
    role: str = "decoratif"
    valeur: object = None
    materiau: str = None
    q: float = None
    label: str = ""
    couleur: str = None
    rotation: tuple = (0.0, 0.0, 0.0)
    operation_cao: str = "aucune"
    identifiant: str = field(default_factory=_identifiant)

    def __post_init__(self):
        if self.forme not in FORMES_SCENE:
            raise ValueError(
                f"Forme de scene inconnue : {self.forme!r}. "
                f"Choix : {FORMES_SCENE}")
        if self.role not in ROLES_SCENE:
            raise ValueError(
                f"Role de scene inconnu : {self.role!r}. Choix : {ROLES_SCENE}")
        if self.operation_cao not in OPERATIONS_CAO:
            raise ValueError(
                f"Opération CAO inconnue : {self.operation_cao!r}. "
                f"Choix : {OPERATIONS_CAO}")
        self.params = dict(self.params)
        rotation = np.asarray(self.rotation, dtype=float)
        if rotation.shape != (3,) or not np.all(np.isfinite(rotation)):
            raise ValueError("La rotation doit contenir trois angles finis.")
        self.rotation = tuple(float(v) for v in rotation)
        self.identifiant = str(self.identifiant or _identifiant())
        if not self.label:
            self.label = self.role.capitalize()
        if self.couleur is None:
            self.couleur = COULEURS_ROLES[self.role]
            if self.role == "electrode" and isinstance(
                    self.valeur, (int, float, np.number)) and self.valeur < 0:
                self.couleur = "#2563eb"

    def libelle_legende(self) -> str:
        details = []
        if self.materiau:
            details.append(self.materiau)
        if self.valeur is not None:
            details.append(str(self.valeur))
        if self.q is not None:
            details.append(f"q={self.q:g}")
        suffixe = f" — {', '.join(details)}" if details else ""
        return f"{self.label} ({self.role}){suffixe}"

    def to_dict(self) -> dict:
        params = dict(self.params)


        params.pop("maillage", None)
        return _json_compatible({
            "identifiant": self.identifiant,
            "forme": self.forme,
            "params": params,
            "role": self.role,
            "valeur": self.valeur,
            "materiau": self.materiau,
            "q": self.q,
            "label": self.label,
            "couleur": self.couleur,
            "rotation": self.rotation,
            "operation_cao": self.operation_cao,
        })

    @classmethod
    def from_dict(cls, donnees: dict) -> "ItemGeometrie":
        champs = dict(donnees)
        return cls(**champs)

    def dupliquer(self) -> "ItemGeometrie":
        copie_item = copy.deepcopy(self)
        copie_item.identifiant = _identifiant()
        copie_item.label = f"{self.label} — copie"
        return copie_item


@dataclass
class Circuit3D:
    points: object
    courant: float = 5.0
    type_circuit: str = "polyligne"
    label: str = "Circuit"
    couleur: str = "#f97316"
    params: dict = field(default_factory=dict)
    identifiant: str = field(default_factory=_identifiant)

    def __post_init__(self):
        points = np.asarray(self.points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2:
            raise ValueError("Un circuit doit avoir la forme (n>=2, 3).")
        if not np.all(np.isfinite(points)):
            raise ValueError("Les coordonnées du circuit doivent être finies.")
        self.points = points.copy()
        self.params = dict(self.params or {})
        self.courant = float(self.courant)
        if not np.isfinite(self.courant):
            raise ValueError("Le courant du circuit doit être fini.")
        self.identifiant = str(self.identifiant or _identifiant())

    def __array__(self, dtype=None):
        return np.asarray(self.points, dtype=dtype)

    def to_dict(self) -> dict:
        return _json_compatible({
            "identifiant": self.identifiant,
            "points": self.points,
            "courant": self.courant,
            "type_circuit": self.type_circuit,
            "label": self.label,
            "couleur": self.couleur,
            "params": self.params,
        })

    @classmethod
    def from_dict(cls, donnees: dict) -> "Circuit3D":
        return cls(**dict(donnees))

    def dupliquer(self) -> "Circuit3D":
        copie_circuit = copy.deepcopy(self)
        copie_circuit.identifiant = _identifiant()
        copie_circuit.label = f"{self.label} — copie"
        return copie_circuit


@dataclass
class Scene3D:
    taille_m: float
    boite_domaine: tuple
    items: list = field(default_factory=list)
    circuits: list = field(default_factory=list)
    materiau_ambiant: str = "Air"
    taille_maille_cao: float = None

    def __post_init__(self):
        self.taille_m = float(self.taille_m)
        if self.taille_m <= 0:
            raise ValueError("La taille physique 3D doit etre strictement positive.")
        if len(self.boite_domaine) != 2:
            raise ValueError("boite_domaine doit contenir (minimum, maximum).")
        minimum = np.asarray(self.boite_domaine[0], dtype=float)
        maximum = np.asarray(self.boite_domaine[1], dtype=float)
        if minimum.shape != (3,) or maximum.shape != (3,):
            raise ValueError("Les bornes de la scene doivent etre des vecteurs 3D.")
        if np.any(maximum <= minimum):
            raise ValueError("Chaque borne maximale doit depasser la borne minimale.")
        self.boite_domaine = (tuple(minimum), tuple(maximum))
        self.items = [
            item if isinstance(item, ItemGeometrie)
            else ItemGeometrie.from_dict(item)
            for item in self.items]
        circuits_valides = []
        for index, circuit in enumerate(self.circuits):
            if isinstance(circuit, Circuit3D):
                circuits_valides.append(circuit)
            elif isinstance(circuit, dict):
                circuits_valides.append(Circuit3D.from_dict(circuit))
            else:
                circuits_valides.append(
                    Circuit3D(circuit, label=f"Circuit {index + 1}"))
        self.circuits = circuits_valides
        self.materiau_ambiant = str(self.materiau_ambiant or "Air")
        if self.taille_maille_cao is not None:
            self.taille_maille_cao = float(self.taille_maille_cao)
            if not np.isfinite(self.taille_maille_cao) or self.taille_maille_cao <= 0:
                raise ValueError("La taille de maille CAO doit être positive.")

    @property
    def items_cao(self) -> list:
        return [item for item in self.items if item.operation_cao != "aucune"]

    @property
    def a_geometrie_cao(self) -> bool:
        return bool(self.items_cao)

    @property
    def bornes_vtk(self) -> tuple:
        minimum, maximum = self.boite_domaine
        return (minimum[0], maximum[0], minimum[1], maximum[1],
                minimum[2], maximum[2])

    @property
    def dimensions(self) -> np.ndarray:
        minimum, maximum = self.boite_domaine
        return np.asarray(maximum) - np.asarray(minimum)

    def to_dict(self) -> dict:
        return {
            "format": "fieldlab-scene-3d",
            "version": 2,
            "taille_m": self.taille_m,
            "boite_domaine": _json_compatible(self.boite_domaine),
            "materiau_ambiant": self.materiau_ambiant,
            "taille_maille_cao": self.taille_maille_cao,
            "items": [item.to_dict() for item in self.items],
            "circuits": [circuit.to_dict() for circuit in self.circuits],
        }

    @classmethod
    def from_dict(cls, donnees: dict) -> "Scene3D":
        if donnees.get("format") not in (None, "fieldlab-scene-3d"):
            raise ValueError("Ce fichier n'est pas une scène FieldLab 3D.")
        return cls(
            taille_m=donnees["taille_m"],
            boite_domaine=donnees["boite_domaine"],
            materiau_ambiant=donnees.get("materiau_ambiant", "Air"),
            taille_maille_cao=donnees.get("taille_maille_cao"),
            items=donnees.get("items", []),
            circuits=donnees.get("circuits", []),
        )

    def sauvegarder_json(self, chemin) -> None:
        with open(chemin, "w", encoding="utf-8") as fichier:
            json.dump(self.to_dict(), fichier, ensure_ascii=False, indent=2)

    @classmethod
    def charger_json(cls, chemin) -> "Scene3D":
        with open(chemin, "r", encoding="utf-8") as fichier:
            return cls.from_dict(json.load(fichier))

    def dupliquer_element(self, index: int):
        elements = self.items + self.circuits
        if not 0 <= index < len(elements):
            raise IndexError("Indice d'élément de scène invalide.")
        element = elements[index].dupliquer()
        if isinstance(element, ItemGeometrie):
            self.items.append(element)
        else:
            self.circuits.append(element)
        return element

    def supprimer_element(self, index: int):
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        index_circuit = index - len(self.items)
        if 0 <= index_circuit < len(self.circuits):
            return self.circuits.pop(index_circuit)
        raise IndexError("Indice d'élément de scène invalide.")


def scene_cube(taille_m: float, items=None, circuits=None,
               materiau_ambiant="Air") -> Scene3D:
    taille_m = float(taille_m)
    return Scene3D(
        taille_m=taille_m,
        boite_domaine=((0.0, 0.0, 0.0), (taille_m, taille_m, taille_m)),
        items=list(items or []),
        circuits=list(circuits or []),
        materiau_ambiant=materiau_ambiant,
    )


def item_depuis_obstacle(obstacle: dict, index: int = 0) -> ItemGeometrie:
    bc = obstacle.get("bc", ("isolant",))
    kind = bc[0]
    role = obstacle.get("role") or {
        "dirichlet": "electrode",
        "isolant": "isolant",
        "materiau": "materiau",
        "source": "source",
    }.get(kind, "decoratif")
    valeur = obstacle.get("valeur")
    q = obstacle.get("q")
    if valeur is None and kind == "dirichlet" and len(bc) > 1:
        valeur = bc[1]
    if q is None and kind == "source" and len(bc) > 1:
        q = bc[1]
    return ItemGeometrie(
        forme=obstacle["forme"],
        params=obstacle["args"],
        role=role,
        valeur=valeur,
        materiau=obstacle.get("materiau"),
        q=q,
        label=obstacle.get("label") or f"Objet {index + 1}",
        couleur=obstacle.get("couleur"),
        rotation=obstacle.get("rotation", (0.0, 0.0, 0.0)),
    )
