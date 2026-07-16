# Packaging FieldLab

FieldLab utilise un bundle PyInstaller **one-dir** : les plugins Qt, VTK, gmsh et ffmpeg sont trop volumineux et trop dynamiques pour qu’un one-file soit fiable ou rapide au démarrage.

## Build local

```bash
uv sync --extra dev
uv run pytest
uv run pyinstaller --clean --noconfirm fieldlab.spec
```

Le spec collecte explicitement `vtkmodules`, `pyvista`, `pyvistaqt` et `imageio_ffmpeg`. Il recherche aussi la bibliothèque native gmsh à côté de `gmsh.py`, car selon l’OS le wheel la place dans `Lib/`, `lib/` ou sous la forme `libgmsh.*`. L’exécutable ffmpeg fourni par `imageio-ffmpeg` est inclus comme donnée du paquet.

## Pièges connus

- **gmsh** : une erreur de chargement de `gmsh-*.dll`, `libgmsh.so` ou `libgmsh.dylib` signifie que la bibliothèque native n’a pas suivi `gmsh.py`. Vérifier le contenu de `dist/FieldLab/_internal` et les chemins collectés pendant l’analyse.
- **Linux/OpenGL** : la machine de build a besoin de `libGL`, `libEGL` et `libGLU`. La CI installe également `libxkbcommon-x11-0`. Sur une machine cible très minimale, les bibliothèques graphiques du système restent requises.
- **Plugins Qt** : le dossier PySide6 `plugins/platforms` doit contenir le plugin de la plateforme (`qwindows`, `qcocoa` ou `qxcb`). Ne pas déplacer uniquement l’exécutable hors du dossier one-dir.
- **VTK/PyVista** : les imports sont dynamiques. Une optimisation agressive des modules cachés peut casser uniquement la vue 3D ; tester au minimum une scène 3D et une capture d’écran.
- **macOS** : `FieldLab.app` n’est ni signé ni notarized. Gatekeeper demandera une confirmation. Une distribution institutionnelle doit ajouter signature Developer ID et notarisation après le build.
- **Windows** : le binaire non signé peut déclencher SmartScreen. La signature Authenticode est une étape de publication externe au workflow actuel.

## Test à froid recommandé

Sur une machine sans Python : décompresser l’archive, lancer FieldLab, ouvrir un scénario 2D dans chacun des trois domaines, ouvrir une scène 3D, puis exporter un PNG et un MP4. Le workflow de release automatise le build natif sur chaque OS, mais ce smoke test reste nécessaire avant d’annoncer une version aux enseignants.
