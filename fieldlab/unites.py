"""Formatage des unités SI et choix d'échelles temporelles physiques."""

from __future__ import annotations

import math
import re


PREFIXES_SI = (
    (1.0e6, "M"),
    (1.0e3, "k"),
    (1.0, ""),
    (1.0e-3, "m"),
    (1.0e-6, "µ"),
    (1.0e-9, "n"),
)


def _nombre_francais(valeur: float, chiffres: int = 3) -> str:
    texte = f"{valeur:.{chiffres}g}"
    return texte.replace(".", ",")


def format_duree(secondes: float) -> str:
    """Formate une durée SI avec une unité lisible, sans changer sa valeur."""

    secondes = float(secondes)
    if not math.isfinite(secondes):
        return "—"
    signe = "−" if secondes < 0 else ""
    valeur = abs(secondes)
    if valeur < 1.0:
        return f"{signe}{_nombre_francais(valeur * 1000.0)} ms"
    if valeur < 60.0:
        return f"{signe}{_nombre_francais(valeur)} s"
    if valeur < 3600.0:
        minutes = int(valeur // 60.0)
        reste = int(round(valeur - 60.0 * minutes))
        if reste == 60:
            minutes += 1
            reste = 0
        return (f"{signe}{minutes} min {reste} s" if reste
                else f"{signe}{minutes} min")
    if valeur < 86400.0:
        heures = int(valeur // 3600.0)
        minutes = int(round((valeur - 3600.0 * heures) / 60.0))
        if minutes == 60:
            heures += 1
            minutes = 0
        return (f"{signe}{heures} h {minutes} min" if minutes
                else f"{signe}{heures} h")
    jours = valeur / 86400.0
    return f"{signe}{_nombre_francais(jours)} j"


def format_grandeur(valeur: float, unite: str, chiffres: int = 3) -> str:
    """Formate une grandeur avec un préfixe SI de n à M."""

    valeur = float(valeur)
    if not math.isfinite(valeur):
        return f"— {unite}".strip()
    absolue = abs(valeur)
    if absolue == 0.0:
        return f"0 {unite}".strip()
    facteur, prefixe = PREFIXES_SI[-1]
    for candidat, prefixe_candidat in PREFIXES_SI:
        if absolue >= candidat:
            facteur, prefixe = candidat, prefixe_candidat
            break
    return f"{_nombre_francais(valeur / facteur, chiffres)} {prefixe}{unite}".strip()


def unite_depuis_libelle(libelle: str) -> str:
    """Extrait l'unité placée entre les dernières parenthèses d'un libellé."""

    correspondance = re.search(r"\(([^()]*)\)\s*$", str(libelle))
    return correspondance.group(1).strip() if correspondance else ""


def arrondir_duree_lisible(secondes: float) -> float:
    """Arrondit une durée à un pas adapté aux réglages d'un cours."""

    secondes = max(float(secondes), 1.0e-3)
    if secondes < 60.0:
        pas = 1.0 if secondes < 10.0 else 5.0
    elif secondes < 3600.0:
        pas = 5.0 * 60.0
    elif secondes < 12.0 * 3600.0:
        pas = 30.0 * 60.0
    elif secondes < 48.0 * 3600.0:
        pas = 3600.0
    else:
        pas = 12.0 * 3600.0
    return max(pas, round(secondes / pas) * pas)


def duree_diffusion_suggeree(
        taille_m: float, kappa: float, rho_cp: float,
        fraction_tau: float = 0.25) -> float:
    """Retourne une durée pédagogique de l'ordre de ``τ/4``.

    Le temps caractéristique de conduction est ``τ = L² / α`` avec
    ``α = κ/(ρ·cp)``. La valeur retournée reste exprimée en vraies secondes.
    """

    taille_m = float(taille_m)
    kappa = float(kappa)
    rho_cp = float(rho_cp)
    if taille_m <= 0.0 or kappa <= 0.0 or rho_cp <= 0.0:
        raise ValueError("L, κ et ρ·cp doivent être strictement positifs.")
    tau = taille_m ** 2 * rho_cp / kappa
    return arrondir_duree_lisible(tau * float(fraction_tau))


def pas_temps_implicite(
        duree: float, n_images: int, sous_pas_par_image: int = 5,
        maximum_pas: int = 2000) -> tuple[float, int]:
    """Choisit le pas d'Euler implicite en bornant le coût du calcul.

    Euler implicite est inconditionnellement stable : les cinq sous-pas par
    image visent la résolution temporelle, pas la stabilité. Le plafond évite
    qu'un grand nombre d'images transforme un calcul pédagogique en calcul
    prohibitif, tout en gardant au moins un pas par intervalle affiché.
    """

    duree = float(duree)
    n_images = int(n_images)
    if duree <= 0.0 or n_images < 2:
        raise ValueError("La durée doit être positive et il faut au moins 2 images.")
    n_pas = min(maximum_pas, max(n_images - 1,
                                (n_images - 1) * sous_pas_par_image))
    return duree / n_pas, n_pas
