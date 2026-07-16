"""Constantes physiques SI partagées par les solveurs."""

import math


EPSILON_0 = 8.854_187_812_8e-12  # F/m
MU_0 = 4.0e-7 * math.pi          # H/m (valeur pédagogique usuelle)


def facteur_source_poisson(domaine_nom: str) -> float:
    """Convertit une densité physique vers le second membre de Poisson.

    - électrostatique : ``-div(εr grad V) = ρ / ε0`` ;
    - magnétostatique 2D : ``-div((1/μr) grad Az) = μ0 Jz`` ;
    - thermique : ``-div(k grad T) = q``.
    """

    if domaine_nom == "Electrostatique":
        return 1.0 / EPSILON_0
    if domaine_nom == "Magnetostatique":
        return MU_0
    if domaine_nom == "Thermique":
        return 1.0
    raise KeyError(f"Domaine inconnu : {domaine_nom!r}")
