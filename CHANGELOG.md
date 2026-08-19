# Historique des changements

Les changements notables de FieldLab sont consignés dans ce fichier. Le format
suit les principes de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/)
et les versions suivent [Semantic Versioning](https://semver.org/lang/fr/).

## [Non publié]

## [2.0.2] - 2026-08-19

### Corrigé

- rétablissement des simulations, maillages et visualisations 3D dans
  l'exécutable Windows ;
- verrouillage de VTK sur la branche 9.5.x, dont les modules utilisés par
  FieldLab passent Smart App Control, contrairement à VTK 9.6.2 sur la machine
  de validation ;
- validation de PyVista, PyVistaQt, Gmsh, des iso-surfaces, flèches, lignes de
  champ, plans de coupe et scènes 3D avec les fichiers marqués comme provenant
  d'Internet.

## [2.0.1] - 2026-08-19

### Corrigé

- remplacement du bundle PyInstaller Windows bloqué par Smart App Control par
  un paquet portable fondé sur le runtime officiel CPython 3.12.10 signé par la
  Python Software Foundation ;
- démarrage de l'interface et chargement de `_ctypes`, Qt, NumPy et SciPy sans
  compte Azure ni certificat payant ;
- repli propre vers l'interface 2D lorsque VTK n'est pas disponible.

### Modifié

- l'édition Windows 2.0.1 désactive la 3D et n'embarque plus VTK, PyVista ni
  Gmsh, dont les modules natifs étaient refusés par la stratégie Microsoft ;
- les éditions macOS/Linux et l'exécution depuis les sources conservent la 3D.

## [2.0.0] - 2026-07-16

### Ajouté

- mode Cours avec paramètres simplifiés et scénarios pédagogiques ;
- interface bilingue français/anglais ;
- simulations 2D et 3D en électrostatique, magnétostatique et thermique ;
- sondes, profils 1D et comparaison d'une référence A avec un résultat B ;
- exports PNG 1080p, 1440p et 4K, CSV, GIF et MP4 horodatés ;
- guide du professeur et documentation de validation scientifique ;
- bundles autonomes multiplateformes construits par GitHub Actions.

### Limites connues

- le thermique fluide est limité à la conduction ;
- le magnétisme 3D utilise Biot–Savart dans le vide ;
- les modèles 2D supposent une invariance hors plan.

[Non publié]: https://github.com/celianchatelet/FieldLab/compare/v2.0.2...HEAD
[2.0.2]: https://github.com/celianchatelet/FieldLab/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/celianchatelet/FieldLab/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/celianchatelet/FieldLab/releases/tag/v2.0.0
