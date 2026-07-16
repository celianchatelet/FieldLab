"""Accès uniforme aux ressources, depuis les sources ou un bundle PyInstaller."""

from pathlib import Path
import sys


def chemin_ressource(*parties: str) -> Path:
    base = Path(getattr(
        sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base.joinpath(*parties)
