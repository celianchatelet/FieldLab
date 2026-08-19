# Composants tiers et licences

FieldLab utilise et, dans ses archives autonomes, redistribue des composants
tiers. Chaque composant reste soumis à sa propre licence. Le fichier `LICENSE`
ne remplace pas ces conditions.

Cette liste décrit les dépendances principales. Les fichiers de licence fournis
par les paquets Python sont également conservés dans le bundle lorsqu'ils sont
présents. Avant une diffusion institutionnelle ou commerciale, un inventaire du
bundle exact doit être vérifié.

## Composants à obligations particulières

### Qt for Python / PySide6 Essentials / Shiboken6

- Usage : interface graphique Qt.
- Licence de l'édition communautaire : LGPL-3.0/GPL-3.0.
- Projet et sources : <https://code.qt.io/cgit/pyside/pyside-setup.git/>
- Conditions : <https://www.qt.io/licensing/open-source-lgpl-obligations>

FieldLab charge les bibliothèques Qt dynamiquement depuis `Lib/site-packages`
sous Windows et depuis le dossier `_internal` des bundles PyInstaller. Elles ne
doivent pas être fusionnées ni empêchées d'être remplacées par l'utilisateur
dans une redistribution relevant de la LGPL.

### Gmsh

- Usage : génération de maillages 3D.
- Licence : GNU GPL version 2 ou ultérieure, avec l'exception de liaison publiée
  par le projet.
- Projet, licence et sources : <https://gmsh.info/>

Gmsh est présent dans les éditions 3D macOS/Linux, mais pas dans l'édition
portable Windows 2.0.1 limitée à la 2D.

### FFmpeg

- Usage : export des animations MP4, appelé comme processus séparé par
  `imageio-ffmpeg`.
- Le binaire Windows actuellement fourni par le paquet est un build statique
  Gyan « essentials » configuré avec `--enable-gpl --enable-version3` et annoncé
  sous GPLv3.
- Licence FFmpeg : <https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md>
- Sources FFmpeg : <https://github.com/FFmpeg/FFmpeg/tree/n7.1>
- Informations sur les builds Gyan : <https://www.gyan.dev/ffmpeg/builds/>

Les builds macOS et Linux doivent être contrôlés de la même manière au moment de
chaque publication, car le binaire livré peut varier selon la plateforme et la
version de `imageio-ffmpeg`.

## Principales bibliothèques Python et scientifiques

| Composant | Usage principal | Licence annoncée par le projet |
| --- | --- | --- |
| Python / runtime embarquable officiel | environnement d'exécution | PSF License |
| NumPy | tableaux et calcul numérique | BSD-3-Clause |
| SciPy | algèbre linéaire creuse | BSD-3-Clause |
| Matplotlib | figures 2D et exports | licence Matplotlib (compatible PSF/BSD) |
| scikit-fem | éléments finis | BSD-3-Clause |
| PyVista | visualisation 3D | MIT |
| PyVistaQt | intégration PyVista/Qt | MIT |
| VTK | moteur de visualisation 3D | BSD-3-Clause |
| imageio | lecture et écriture d'images/animations | BSD-2-Clause |
| imageio-ffmpeg | enveloppe Python de FFmpeg | BSD-2-Clause |
| Pillow | traitement d'images | HPND |
| meshio | échange de maillages | MIT |
| PyInstaller | construction des bundles macOS/Linux | GPL-2.0-or-later avec exception pour le bootloader |

PyVista, PyVistaQt, VTK 9.5.x et Gmsh sont de nouveau redistribués dans l'édition
Windows à partir de la version 2.0.2 afin de fournir la 3D.

Les versions exactes et leurs empreintes sont verrouillées dans `uv.lock`. Les
dépendances transitives peuvent ajouter d'autres avis ; leurs fichiers de licence
doivent rester associés aux fichiers redistribués.

## Absence d'approbation

Les noms des projets et de leurs auteurs sont cités uniquement pour satisfaire
aux obligations d'attribution. Ils n'impliquent aucune approbation de FieldLab
par ces projets ou leurs auteurs.
