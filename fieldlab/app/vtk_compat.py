"""Chargement facultatif de la visualisation VTK/PyVista.

Le paquet Windows portable désactive VTK lorsque Smart App Control refuse ses
extensions natives. Les simulations et visualisations 2D restent disponibles.
"""

from dataclasses import dataclass, field as dataclass_field
import os
from types import SimpleNamespace

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from fieldlab.fem3d.calques import (
    CalquesRendu3D, OptionsGraines3D, calques_depuis_mode,
)


THREE_D_AVAILABLE = False
THREE_D_ERROR = None

if os.environ.get("FIELDLAB_DISABLE_VTK") != "1":
    try:
        from pyvistaqt import QtInteractor
        from vtkmodules.vtkRenderingCore import vtkCellPicker

        from fieldlab.app import viz3d
        from fieldlab.fem3d import render as fem3d_render

        THREE_D_AVAILABLE = True
    except (ImportError, OSError, RuntimeError) as error:
        THREE_D_ERROR = error
else:
    THREE_D_ERROR = RuntimeError(
        "La visualisation 3D est désactivée dans ce paquet Windows.")


if not THREE_D_AVAILABLE:
    class QtInteractor(QWidget):
        """Remplacement léger permettant à l'interface 2D de démarrer."""

        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            message = QLabel(
                "Vue 3D indisponible sur ce PC.\n"
                "Les simulations et visualisations 2D restent disponibles.")
            message.setWordWrap(True)
            layout.addWidget(message)

        def add_text(self, *_args, **_kwargs):
            return None

        def clear(self):
            return None

        def disable_picking(self):
            return None

        def reset_camera(self):
            return None

        def set_background(self, *_args, **_kwargs):
            return None

        def view_isometric(self):
            return None

        def view_xy(self):
            return None

        def view_xz(self):
            return None


    class vtkCellPicker:
        def SetTolerance(self, _tolerance):
            return None


    @dataclass
    class PlanCoupe3D:
        normale: tuple = (1.0, 0.0, 0.0)
        origine: tuple = (0.5, 0.5, 0.5)


    @dataclass
    class OptionsCoupe3D:
        active: bool = False
        plans: list = dataclass_field(default_factory=list)
        fond_scalaire: bool = True
        isolignes: bool = True
        vecteurs_projetes: bool = False
        lignes_champ: bool = False
        orientation_libre: bool = False
        clip_boite: bool = False
        bornes_clip: tuple = None
        manipuler_widget: bool = False


    @dataclass
    class SourceLignes3D:
        centre: tuple = None
        normale: tuple = (0.0, 0.0, 1.0)


    @dataclass
    class OptionsRendu3D:
        courbe_volume: str = "Sigmoïde"
        nombre_isosurfaces: int = 8
        fraction_iso_min: float = 0.05
        fraction_iso_max: float = 0.95
        pas_glyphes: int = 4
        taille_glyphes: float = 0.12
        source_lignes: SourceLignes3D = dataclass_field(
            default_factory=SourceLignes3D)
        taille_source_lignes: float = 0.55
        densite_lignes: int = 7
        rayon_tubes: float = 0.004
        graines: OptionsGraines3D = dataclass_field(
            default_factory=OptionsGraines3D)


    def _indisponible(*_args, **_kwargs):
        raise RuntimeError(str(THREE_D_ERROR))


    fem3d_render = SimpleNamespace(
        MODES_RENDU=(
            "Carte scalaire", "Iso-valeurs", "Champ (flèches)",
            "Lignes de champ"),
        SCALAIRES_3D=(
            "Scalaire principal", "Intensité du champ",
            "Coefficient matériau κ"),
        CalquesRendu3D=CalquesRendu3D,
        OptionsCoupe3D=OptionsCoupe3D,
        OptionsRendu3D=OptionsRendu3D,
        PlanCoupe3D=PlanCoupe3D,
        calques_depuis_mode=calques_depuis_mode,
        dessiner=_indisponible,
        dessiner_scene_seule=_indisponible,
    )
    viz3d = SimpleNamespace(dessiner=_indisponible)
