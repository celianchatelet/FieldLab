# -*- mode: python ; coding: utf-8 -*-
"""Bundle one-dir FieldLab, volontairement explicite pour VTK/gmsh/ffmpeg."""

from pathlib import Path
import sys

from PIL import Image
from PyInstaller.utils.hooks import (
    collect_data_files, collect_dynamic_libs, get_module_file_attribute,
)


racine = Path(SPECPATH)


def creer_icones():
    """Produit les formats natifs depuis le logo officiel de FieldLab."""

    dossier = racine / "build" / "fieldlab-icons"
    dossier.mkdir(parents=True, exist_ok=True)
    source = racine / "assets" / "fieldlab_icon.png"
    with Image.open(source) as logo:
        image = logo.convert("RGBA").resize(
            (1024, 1024), Image.Resampling.LANCZOS)
    png = dossier / "fieldlab.png"
    ico = dossier / "fieldlab.ico"
    icns = dossier / "fieldlab.icns"
    image.save(png)
    image.save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64),
                           (128, 128), (256, 256)])
    image.save(icns)
    return png, ico, icns


icone_png, icone_ico, icone_icns = creer_icones()
icone_executable = (
    icone_ico if sys.platform == "win32"
    else icone_icns if sys.platform == "darwin"
    else icone_png)

datas = [(str(racine / "assets" / "fieldlab_icon.png"), "assets")]
binaries = []
hiddenimports = []

# VTK charge ses moteurs de rendu dynamiquement. ``vtkmodules.all`` couvre les
# modules natifs sans embarquer les adaptateurs de test GTK/Wx. Les données
# ffmpeg contiennent l'exécutable propre à chaque plateforme.
binaries += collect_dynamic_libs("vtkmodules")
datas += collect_data_files("imageio_ffmpeg")
hiddenimports += [
    "vtkmodules.all",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
    "vtkmodules.vtkRenderingOpenGL2",
    "vtkmodules.vtkRenderingContextOpenGL2",
    "vtkmodules.vtkRenderingFreeType",
    "vtkmodules.vtkInteractionStyle",
    "pyvista",
    "pyvistaqt",
    "imageio_ffmpeg",
]

# gmsh est distribué comme un module gmsh.py et une bibliothèque native placée
# à côté de site-packages (Lib sous Windows, lib sous Unix).
module_gmsh = Path(get_module_file_attribute("gmsh"))
for dossier in (module_gmsh.parent, module_gmsh.parent.parent):
    for motif in ("gmsh*.dll", "libgmsh*.so*", "libgmsh*.dylib"):
        for bibliotheque in dossier.glob(motif):
            binaries.append((str(bibliotheque), "."))

a = Analysis(
    [str(racine / "main.py")],
    pathex=[str(racine)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FieldLab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icone_executable),
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FieldLab",
)

if sys.platform == "darwin":
    app = BUNDLE(
        collection,
        name="FieldLab.app",
        icon=str(icone_icns),
        bundle_identifier="org.fieldlab.simulator",
        info_plist={"NSHighResolutionCapable": True},
    )
