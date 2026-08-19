# FieldLab 2

[![CI](https://github.com/celianchatelet/FieldLab/actions/workflows/ci.yml/badge.svg)](https://github.com/celianchatelet/FieldLab/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)

![FieldLab en mode Cours](https://raw.githubusercontent.com/celianchatelet/FieldLab/main/docs/images/fieldlab-cours.png)

FieldLab est un laboratoire pédagogique multiphysique 2D/3D consacré à
l'électrostatique, à la magnétostatique et aux transferts thermiques. Il vise
l'enseignement et l'exploration de modèles physiques, avec une interface en
français ou en anglais.

Le mode **Cours** propose des scénarios prêts à simuler et des exports adaptés
aux supports pédagogiques. Le mode **Expert** donne accès au maillage, aux
solveurs et aux conditions aux limites.

> FieldLab est un outil pédagogique. Ce n'est pas un logiciel de calcul certifié
> pour le dimensionnement ou la validation d'un système d'ingénierie.

## Fonctionnalités principales

- simulations 2D et 3D en électrostatique, magnétostatique et thermique ;
- scénarios pédagogiques : condensateur plan, cage de Faraday, fils parallèles,
  bobines de Helmholtz, mur composite, trempe thermique, etc. ;
- cartes scalaires, vecteurs, lignes de champ, coupes et sondes ;
- profils quantitatifs et comparaison entre une référence A et un résultat B ;
- régimes stationnaires et transitoires selon le domaine ;
- exports PNG jusqu'en 4K, CSV, GIF et MP4 horodatés ;
- interface bilingue français/anglais.

## Télécharger et lancer l'application

Les versions autonomes sont publiées dans la page
[Releases](https://github.com/celianchatelet/FieldLab/releases). Choisissez
l'archive correspondant à votre système :

- `FieldLab-Windows.zip` ;
- `FieldLab-macOS.zip` ;
- `FieldLab-Linux.tar.gz`.

Python n'est pas nécessaire pour utiliser ces versions.

### Windows

1. Téléchargez puis décompressez **entièrement** l'archive.
2. Ouvrez le dossier `FieldLab`.
3. Double-cliquez sur `FieldLab.exe`.

Ne déplacez pas `FieldLab.exe` hors de son dossier : les DLL et le répertoire
`Lib` placés à côté contiennent les bibliothèques nécessaires.

### macOS

Décompressez l'archive puis ouvrez `FieldLab.app`. Si Gatekeeper bloque le
premier lancement, faites un clic droit sur l'application, choisissez **Ouvrir**
et confirmez.

### Linux

Décompressez l'archive puis lancez `FieldLab/FieldLab`. Si nécessaire :

```bash
chmod +x FieldLab/FieldLab
```

### Avertissement de sécurité du système

La version Windows 2.0.0 n'est pas compatible avec Smart App Control. À partir
de la version 2.0.1, l'archive Windows utilise le runtime Python officiel signé
par la **Python Software Foundation** et ne nécessite aucun service Azure.
Vérifiez ce signataire dans l'onglet **Signatures numériques** des propriétés de
`FieldLab.exe`.

Pour éviter les DLL VTK refusées par certaines stratégies Microsoft, l'édition
Windows 2.0.1 fournit les simulations, mesures et exports **2D** et désactive la
3D. La 3D reste disponible sous macOS/Linux et lors d'une exécution depuis les
sources.

Chaque archive publiée est accompagnée d'un fichier `.sha256` permettant d'en
vérifier l'intégrité.

## Première utilisation en cours

1. Sélectionnez un domaine et un scénario.
2. Gardez d'abord les paramètres proposés et cliquez sur **Simuler**.
3. Ajoutez des sondes ou tracez un profil 1D pour obtenir des valeurs
   quantitatives.
4. Modifiez un seul paramètre, puis comparez le résultat à la référence.
5. Exportez une image, un profil ou une animation pour votre support de cours.

Le [Guide du professeur](docs/GUIDE_PROFESSEUR.md) propose des activités et des
objectifs d'apprentissage. Le fichier [LISEZ-MOI](LISEZ-MOI.txt) reprend les
instructions de lancement fournies avec chaque archive.

## Périmètre et hypothèses physiques

- Les unités et les propriétés des matériaux sont exprimées en SI.
- En thermique des fluides, FieldLab simule la **conduction pure** : la
  convection naturelle et l'écoulement ne sont pas résolus.
- Le magnétisme 3D repose sur Biot–Savart dans le vide. Les matériaux
  ferromagnétiques n'y modifient pas le champ.
- Un modèle 2D représente une géométrie invariante dans la direction hors plan.
  Les charges et courants sont donc volumiques dans cette coupe extrudée.
- Une visualisation convaincante ne suffit pas à démontrer la convergence :
  vérifiez le maillage, les conditions aux limites et la sensibilité des sondes.

Les contrôles analytiques et numériques actuellement automatisés sont décrits
dans [Validation scientifique](docs/VALIDATION.md).

## Documentation

- [Guide du professeur](docs/GUIDE_PROFESSEUR.md)
- [Validation scientifique et limites](docs/VALIDATION.md)
- [Construction des exécutables](docs/PACKAGING.md)
- [Internationalisation](docs/I18N.md)
- [Historique des changements](CHANGELOG.md)
- [Contribuer](CONTRIBUTING.md)
- [Citer FieldLab](CITATION.cff)

## Développement

Prérequis : [uv](https://docs.astral.sh/uv/) et Python 3.10 ou plus récent.

```bash
git clone https://github.com/celianchatelet/FieldLab.git
cd FieldLab
uv sync --extra dev
uv run fieldlab
```

Avant toute proposition de modification :

```bash
uv run ruff check --select E9,F63,F7,F82 fieldlab tests main.py
uv run pytest -q
```

Pour construire l'archive Windows locale :

```powershell
.\scripts\build_windows.ps1
```

Pour construire le bundle PyInstaller macOS/Linux :

```bash
uv run pyinstaller --clean --noconfirm fieldlab.spec
```

Le résultat PyInstaller se trouve dans `dist/FieldLab`. Un tag correspondant exactement à
la version du `pyproject.toml`, par exemple `v2.0.1`, déclenche les builds natifs
Windows, macOS et Linux et les publie dans une GitHub Release.

## Licence

La licence propre à FieldLab est indiquée dans le fichier `LICENSE`. Les
composants tiers intégrés ou utilisés par l'application restent soumis à leurs
licences respectives, recensées dans `THIRD_PARTY_NOTICES.md`.

Si FieldLab est utilisé dans un cours, une publication ou un autre travail
académique, les métadonnées de citation sont disponibles dans `CITATION.cff`.

## Auteur

**Célian Chatelet**<br>
Institut Polytechnique des Sciences Avancées<br>
63 boulevard de Brandebourg, Ivry-sur-Seine, France

## English summary

FieldLab is a bilingual 2D/3D teaching laboratory for electrostatics,
magnetostatics and heat transfer. Classroom mode provides ready-to-run
activities and presentation-ready exports, while Expert mode exposes meshes,
solvers and boundary conditions. Standalone builds are available from the
[Releases page](https://github.com/celianchatelet/FieldLab/releases); Python is
not required. FieldLab is intended for teaching and numerical exploration, not
for certified engineering work.
