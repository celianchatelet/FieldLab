# Packaging et publication de FieldLab

FieldLab utilise un bundle PyInstaller **one-dir**. Les plugins Qt, VTK, Gmsh
et FFmpeg sont trop volumineux et trop dynamiques pour qu'un exécutable unique
soit aussi fiable et rapide au démarrage.

## Construire et archiver sous Windows

La commande recommandée exécute les tests, reconstruit le bundle, ajoute la
documentation visible et produit une archive accompagnée de son empreinte
SHA-256 :

```powershell
.\scripts\build_windows.ps1
```

Options utiles pendant le développement :

```powershell
# Réutiliser le dossier dist/FieldLab existant
.\scripts\build_windows.ps1 -SkipBuild

# Reconstruire sans relancer les tests
.\scripts\build_windows.ps1 -SkipTests
```

Les résultats sont `FieldLab-Windows.zip` et
`FieldLab-Windows.zip.sha256` à la racine du projet.

## Build PyInstaller seul

```bash
uv sync --extra dev
uv run pytest -q
uv run pyinstaller --clean --noconfirm fieldlab.spec
```

Le bundle brut se trouve dans `dist/FieldLab`. Il ne faut jamais distribuer
`FieldLab.exe` seul : le dossier `_internal` placé à côté est indispensable.

## Contenu d'une archive publiée

Chaque archive finale contient :

- l'application et ses bibliothèques ;
- `LISEZ-MOI.txt` avec les instructions de lancement ;
- `GUIDE_PROFESSEUR.md` ;
- `LICENSE` ;
- `THIRD_PARTY_NOTICES.md` ;
- `CITATION.cff`.

Le spec collecte explicitement `vtkmodules`, `pyvista`, `pyvistaqt` et
`imageio_ffmpeg`. Il recherche aussi la bibliothèque native Gmsh à côté de
`gmsh.py`, car le wheel peut la placer dans `Lib/`, `lib/` ou sous la forme
`libgmsh.*`. L'exécutable FFmpeg fourni par `imageio-ffmpeg` est inclus comme
donnée du paquet.

## Publication GitHub

Le workflow `.github/workflows/release.yml` est déclenché par un tag `v*`. Il :

1. vérifie que le tag correspond à la version de `pyproject.toml` ;
2. vérifie `uv.lock` et exécute les tests ;
3. construit un bundle natif sous Windows, macOS et Linux ;
4. ajoute les documents de distribution ;
5. calcule une empreinte SHA-256 ;
6. joint les archives et les empreintes à la GitHub Release.

Exemple pour la version 2.0.0 :

```bash
git tag -a v2.0.0 -m "FieldLab 2.0.0"
git push origin v2.0.0
```

Ne créez le tag qu'après validation du commit sur lequel il pointe.

## Pièges connus

- **Gmsh** : une erreur de chargement de `gmsh-*.dll`, `libgmsh.so` ou
  `libgmsh.dylib` signifie que la bibliothèque native n'a pas suivi `gmsh.py`.
- **Linux/OpenGL** : la machine de build a besoin de `libGL`, `libEGL` et
  `libGLU`. Une machine cible minimale peut encore nécessiter des bibliothèques
  graphiques système.
- **Plugins Qt** : le dossier `PySide6/plugins/platforms` doit contenir le plugin
  natif (`qwindows`, `qcocoa` ou `qxcb`).
- **VTK/PyVista** : les imports sont dynamiques. Tester une scène 3D après toute
  modification du spec ou des exclusions.
- **macOS** : `FieldLab.app` n'est ni signé ni notarisé. Gatekeeper demandera une
  confirmation au premier lancement.
- **Windows** : le binaire non signé peut déclencher SmartScreen. Une signature
  Authenticode est nécessaire pour supprimer cet avertissement de confiance.
- **Licences** : le bundle contient des bibliothèques LGPL/GPL et un binaire
  FFmpeg GPLv3. Vérifier `THIRD_PARTY_NOTICES.md` et conserver les avis associés.

## Test à froid obligatoire avant diffusion

Sur une machine sans Python :

1. télécharger l'archive depuis le même lien que les destinataires ;
2. vérifier son SHA-256 puis la décompresser ;
3. lancer FieldLab ;
4. ouvrir un scénario 2D dans chacun des trois domaines ;
5. ouvrir une scène 3D et vérifier la rotation ;
6. exporter un PNG et un MP4 ;
7. fermer puis relancer l'application.

Ce test manuel reste nécessaire même si la construction et les tests automatisés
réussissent.
