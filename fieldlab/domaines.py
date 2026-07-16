from dataclasses import dataclass
from typing import Callable

from fieldlab import geometries, magneto, thermique
from fieldlab.field import champ_electrique, champ_magnetique, flux_thermique


@dataclass
class Domaine:
    nom: str
    titre: str


    scenarios: dict
    champ_fn: Callable
    scalaire: str
    champ: str
    label_val: str
    defaut: float
    walls_defaut: Callable
    wall_types: tuple




    scenarios_essentiels: tuple = ()


_BASE = ("neumann", "dirichlet")
_THERMIQUE = ("neumann", "dirichlet")

DOMAINES = {
    "Electrostatique": Domaine(
        nom="Electrostatique",
        titre="Électricité",
        scenarios=geometries.GEOMETRIES,
        champ_fn=champ_electrique,
        scalaire="Potentiel V (V)",
        champ="Champ E (V/m)",
        label_val="Tension (V)",
        defaut=10.0,
        walls_defaut=geometries.walls_defaut,
        wall_types=_BASE,
        scenarios_essentiels=(
            "Condensateur plan", "Dipole (deux disques)", "Cable coaxial",
            "Cage de Faraday", "Pointe - plan (effet de pointe)",
            "Condensateur avec diélectrique partiel", "Ligne bifilaire"),
    ),
    "Magnetostatique": Domaine(
        nom="Magnetostatique",
        titre="Magnétisme",
        scenarios=magneto.SCENARIOS,
        champ_fn=champ_magnetique,




        scalaire="Potentiel A_z (T·m)",
        champ="Champ B (T)",
        label_val="Densité de courant J (A/m²)",
        defaut=100000.0,
        walls_defaut=magneto.walls_defaut,
        wall_types=_BASE,
        scenarios_essentiels=(
            "Fil unique", "Deux fils (opposes)", "Boucle de courant (dipole)",
            "Solenoide (coupe)"),
    ),
    "Thermique": Domaine(
        nom="Thermique",
        titre="Thermique",
        scenarios=thermique.SCENARIOS,
        champ_fn=flux_thermique,
        scalaire="Température T (°C)",
        champ="Flux thermique (W/m²)",
        label_val="Température chaude",
        defaut=100.0,
        walls_defaut=thermique.walls_defaut,
        wall_types=_THERMIQUE,
        scenarios_essentiels=(
            "Mur composite (verre + plastique)",
            "Ailette de refroidissement",
            "Trempe (objet chaud dans l'eau)",
            "Pont thermique", "Plancher chauffant",
            "Tuyau chaud (enceinte froide)"),
    ),
}

NOMS_DOMAINES = list(DOMAINES)
