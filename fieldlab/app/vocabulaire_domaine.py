"""Vocabulaire d'interface propre à chaque domaine physique.

Les rôles retournés par ce module sont les clés internes historiques attendues
par le moteur et par la sérialisation. Les libellés ne servent qu'à l'affichage.
"""

from __future__ import annotations


_VOCABULAIRES = {
    "Electrostatique": {
        "natures": ("Primitive",),
        "roles": (
            "electrode", "isolant", "materiau", "conducteur", "source",
            "decoratif",
        ),
        "roles_affiches": {
            "electrode": "Potentiel imposé",
            "isolant": "Isolant électrique",
            "materiau": "Matériau diélectrique",
            "conducteur": "Conducteur",
            "source": "Charge volumique",
            "decoratif": "Décoratif (sans effet physique)",
        },
        "valeur": {"electrode": "Potentiel imposé V (V)"},
        "q": {"source": "Charge volumique ρ (C/m³)"},
        "parametre_2d": "Tension V (V)",
        "conditions_limites_3d": {
            "neumann": {
                "libelle": "Isolation électrique (flux normal nul)",
                "parametres": (None, None),
                "defauts": (0.0, 0.0),
            },
            "dirichlet": {
                "libelle": "Potentiel imposé",
                "parametres": ("Potentiel V (V)", None),
                "defauts": (0.0, 0.0),
            },
        },
        "aide_conditions_limites_3d": (
            "Conditions appliquées aux six faces externes de la boîte. "
            "Une isolation impose un flux électrique normal nul ; un "
            "potentiel imposé fixe V sur toute la face."),
    },
    "Thermique": {
        "natures": ("Primitive",),
        "roles": (
            "electrode", "isolant", "materiau", "source", "decoratif",
        ),
        "roles_affiches": {
            "electrode": "Température imposée",
            "isolant": "Paroi adiabatique",
            "materiau": "Matériau thermique",
            "source": "Source de chaleur",
            "decoratif": "Décoratif (sans effet physique)",
        },
        "valeur": {"electrode": "Température imposée T (°C)"},
        "q": {"source": "Puissance volumique q (W/m³)"},
        "parametre_2d": "Température (°C)",
        "conditions_limites_3d": {
            "neumann": {
                "libelle": "Paroi adiabatique",
                "parametres": (None, None),
                "defauts": (0.0, 0.0),
            },
            "dirichlet": {
                "libelle": "Température imposée",
                "parametres": ("Température T (°C)", None),
                "defauts": (20.0, 0.0),
            },
            "robin": {
                "libelle": "Convection",
                "parametres": (
                    "Coefficient h (W/m²·K)", "Température ambiante T∞ (°C)"),
                "defauts": (10.0, 20.0),
            },
            "radiation": {
                "libelle": "Rayonnement",
                "parametres": (
                    "Émissivité ε (0–1)", "Température ambiante T∞ (°C)"),
                "defauts": (0.9, 20.0),
            },
            "flux": {
                "libelle": "Flux thermique imposé",
                "parametres": ("Flux q (W/m²)", None),
                "defauts": (0.0, 0.0),
            },
        },
        "aide_conditions_limites_3d": (
            "Conditions appliquées aux six faces externes de la boîte : "
            "adiabatique, température imposée, convection, rayonnement ou "
            "flux thermique imposé."),
    },
    "Magnetostatique": {
        "natures": ("Primitive", "Circuit"),
        "roles": ("decoratif",),
        "roles_affiches": {
            "source": "Source de courant",
            "materiau": "Matériau magnétique",
            "decoratif": "Repère visuel (sans effet magnétique)",
        },
        "valeur": {},
        "q": {},
        "parametre_2d": "Densité de courant J (A/m²)",
        "conditions_limites_3d": {},
        "aide_conditions_limites_3d": "",
    },
}


def _vocabulaire(domaine_nom: str) -> dict:
    try:
        return _VOCABULAIRES[domaine_nom]
    except KeyError as erreur:
        raise ValueError(f"Domaine physique inconnu : {domaine_nom!r}.") from erreur


def natures_autorisees(domaine_nom: str) -> tuple[str, ...]:
    """Retourne les natures d'élément proposées par l'interface 3D."""

    return _vocabulaire(domaine_nom)["natures"]


def roles_autorises(domaine_nom: str) -> tuple[str, ...]:
    """Retourne les clés de rôle proposées pour une primitive 3D."""

    return _vocabulaire(domaine_nom)["roles"]


def libelle_role(domaine_nom: str, role: str) -> str:
    """Retourne le nom visible d'un rôle sans modifier sa clé interne."""

    return _vocabulaire(domaine_nom)["roles_affiches"].get(role, role)


def libelle_valeur(domaine_nom: str, role: str) -> str | None:
    """Retourne le libellé du champ ``valeur``, ou ``None`` s'il est inutile."""

    return _vocabulaire(domaine_nom)["valeur"].get(role)


def libelle_q(domaine_nom: str, role: str) -> str | None:
    """Retourne le libellé du champ ``q``, ou ``None`` s'il est inutile."""

    return _vocabulaire(domaine_nom)["q"].get(role)


def libelle_parametre_2d(domaine_nom: str) -> str:
    """Retourne le libellé de la valeur de référence du panneau 2D."""

    return _vocabulaire(domaine_nom)["parametre_2d"]


def conditions_limites_3d(domaine_nom: str) -> tuple[str, ...]:
    """Retourne les clés de conditions proposées sur les faces du domaine."""

    return tuple(_vocabulaire(domaine_nom)["conditions_limites_3d"])


def libelle_condition_limite_3d(domaine_nom: str, condition: str) -> str:
    """Retourne le libellé visible d'une condition aux limites 3D."""

    conditions = _vocabulaire(domaine_nom)["conditions_limites_3d"]
    try:
        return conditions[condition]["libelle"]
    except KeyError as erreur:
        raise ValueError(
            f"Condition 3D inconnue pour {domaine_nom} : {condition!r}.") \
            from erreur


def libelles_parametres_condition_limite_3d(
        domaine_nom: str, condition: str) -> tuple[str | None, str | None]:
    """Retourne les deux libellés de paramètres d'une condition 3D."""

    conditions = _vocabulaire(domaine_nom)["conditions_limites_3d"]
    try:
        return conditions[condition]["parametres"]
    except KeyError as erreur:
        raise ValueError(
            f"Condition 3D inconnue pour {domaine_nom} : {condition!r}.") \
            from erreur


def defauts_condition_limite_3d(
        domaine_nom: str, condition: str) -> tuple[float, float]:
    """Retourne les valeurs initiales adaptées à une condition 3D."""

    conditions = _vocabulaire(domaine_nom)["conditions_limites_3d"]
    try:
        return conditions[condition]["defauts"]
    except KeyError as erreur:
        raise ValueError(
            f"Condition 3D inconnue pour {domaine_nom} : {condition!r}.") \
            from erreur


def aide_conditions_limites_3d(domaine_nom: str) -> str:
    """Retourne l'aide contextuelle du groupe de parois 3D."""

    return _vocabulaire(domaine_nom)["aide_conditions_limites_3d"]
