"""Registre des domaines physiques.

Chaque Domaine devient un onglet autonome. Il porte aussi, en plus du champ
derive et des libelles : la bibliotheque de parois recommandees par scenario
(walls_defaut) et la liste des types de parois autorises (wall_types).
"""
from dataclasses import dataclass
from typing import Callable

from fieldlab import geometries, magneto, thermique
from fieldlab.field import champ_electrique, champ_magnetique, flux_thermique


@dataclass
class Domaine:
    nom: str
    scenarios: dict
    champ_fn: Callable
    scalaire: str
    champ: str
    label_val: str
    defaut: float
    walls_defaut: Callable          # (nom, val) -> dict de parois
    wall_types: tuple               # types de parois proposes dans l'UI


_BASE = ("neumann", "dirichlet")
_THERMIQUE = ("neumann", "dirichlet")

DOMAINES = {
    "Electrostatique": Domaine(
        nom="Electrostatique",
        scenarios=geometries.GEOMETRIES,
        champ_fn=champ_electrique,
        scalaire="Potentiel V",
        champ="Champ E",
        label_val="Tension (V)",
        defaut=10.0,
        walls_defaut=geometries.walls_defaut,
        wall_types=_BASE,
    ),
    "Magnetostatique": Domaine(
        nom="Magnetostatique",
        scenarios=magneto.SCENARIOS,
        champ_fn=champ_magnetique,
        scalaire="Potentiel A_z",
        champ="Champ B",
        label_val="Courant J",
        defaut=20.0,
        walls_defaut=magneto.walls_defaut,
        wall_types=_BASE,
    ),
    "Thermique": Domaine(
        nom="Thermique",
        scenarios=thermique.SCENARIOS,
        champ_fn=flux_thermique,
        scalaire="Temperature T",
        champ="Flux thermique",
        label_val="Temperature chaude",
        defaut=100.0,
        walls_defaut=thermique.walls_defaut,
        wall_types=_THERMIQUE,
    ),
}

NOMS_DOMAINES = list(DOMAINES)
