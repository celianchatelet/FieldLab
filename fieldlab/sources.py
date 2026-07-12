import numpy as np


def sinusoidale(t: float, amplitude: float, frequence: float, phase: float = 0.0) -> float:
    return amplitude * np.sin(2.0 * np.pi * frequence * t + phase)


def creneau(t: float, amplitude: float, frequence: float, rapport_cyclique: float = 0.5) -> float:
    phase = (t * frequence) % 1.0
    return amplitude if phase < rapport_cyclique else -amplitude


def impulsions(t: float, amplitude: float, frequence: float, largeur: float = 0.1) -> float:
    phase = (t * frequence) % 1.0
    return amplitude if phase < largeur else 0.0


def echelon(t: float, amplitude: float, frequence: float) -> float:
    t_bascule = 1.0 / frequence if frequence > 0 else 0.0
    return amplitude if t >= t_bascule else 0.0


FORMES_TEMPORELLES = {
    "Sinusoidale": sinusoidale,
    "Creneau": creneau,
    "Impulsions": impulsions,
    "Echelon": echelon,
}
NOMS_FORMES = list(FORMES_TEMPORELLES)
