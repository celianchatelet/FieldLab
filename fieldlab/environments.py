from dataclasses import dataclass

_ZERO_ABSOLU_C = -273.15


@dataclass(frozen=True)
class Environnement:
    nom: str
    materiau_fond: str
    h_convection: float
    emissivite: float
    t_ambiante: float
    description: str = ""


ENVIRONNEMENTS: dict[str, Environnement] = {
    "Air (laboratoire)": Environnement(
        "Air (laboratoire)", materiau_fond="Air", h_convection=8.0,
        emissivite=0.9, t_ambiante=20.0,
        description="Air interieur calme : convection naturelle modeste."),
    "Atmosphere terrestre (exterieur)": Environnement(
        "Atmosphere terrestre (exterieur)", materiau_fond="Air", h_convection=20.0,
        emissivite=0.9, t_ambiante=15.0,
        description="Air exterieur avec vent leger : convection forcee, "
                     "plus efficace qu'en interieur calme."),
    "Vide spatial": Environnement(
        "Vide spatial", materiau_fond="Vide", h_convection=0.0,
        emissivite=0.9, t_ambiante=_ZERO_ABSOLU_C + 2.7,
        description="Aucune convection possible ; seul le rayonnement "
                     "echange de la chaleur, vers le fond cosmique (~2.7 K)."),
    "Eau": Environnement(
        "Eau", materiau_fond="Eau", h_convection=500.0,
        emissivite=0.95, t_ambiante=15.0,
        description="Immersion dans l'eau : convection tres efficace (liquide)."),
    "Huile": Environnement(
        "Huile", materiau_fond="Huile", h_convection=100.0,
        emissivite=0.9, t_ambiante=20.0,
        description="Immersion dans l'huile (refroidissement de transformateur "
                     "par exemple) : convection efficace mais moindre que l'eau."),
}

NOMS_ENVIRONNEMENTS = list(ENVIRONNEMENTS)
