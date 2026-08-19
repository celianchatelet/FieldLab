# Packaging et publication de FieldLab

FieldLab utilise deux formats de distribution :

- Windows : un paquet Python portable compatible avec Smart App Control ;
- macOS et Linux : un bundle PyInstaller **one-dir**.

## Construire et archiver sous Windows

La commande recommandée exécute les tests, construit le paquet portable, ajoute
la documentation puis produit l'archive et son empreinte SHA-256 :

```powershell
.\scripts\build_windows.ps1
```

Options utiles pendant le développement :

```powershell
# Réutiliser release/FieldLab
.\scripts\build_windows.ps1 -SkipBuild

# Reconstruire sans relancer les tests
.\scripts\build_windows.ps1 -SkipTests
```

Le constructeur interne peut aussi être appelé directement :

```powershell
.\scripts\build_windows_portable.ps1 -OutputDirectory release\FieldLab
```

Il télécharge le paquet embarquable officiel CPython 3.12.10, vérifie son
SHA-256 (`4ACBED6DD1C744B0376E3B1CF57CE906F9DC9E95E68824584C8099A63025A3C3`),
installe les dépendances verrouillées et copie les sources de FieldLab. Le
lanceur `FieldLab.exe` est une copie, sans modification binaire, de
`pythonw.exe` : sa signature Authenticode de la Python Software Foundation reste
donc valide.

Smart App Control refuse les extensions VTK diffusées sur PyPI sur certaines
machines. Elles ne sont pas incluses dans l'archive Windows 2.0.1 : la 3D est
désactivée dans cette édition, tandis que les simulations, mesures et exports 2D
restent disponibles. Les versions macOS/Linux et l'exécution depuis les sources
conservent la 3D.

Ne distribuez jamais `FieldLab.exe` seul. Les DLL du runtime et le dossier
`Lib\site-packages` placés à côté sont indispensables.

## Construire sous macOS et Linux

```bash
uv sync --extra dev
uv run pytest -q
uv run pyinstaller --clean --noconfirm fieldlab.spec
```

Le résultat brut se trouve dans `dist/FieldLab.app` sous macOS et
`dist/FieldLab` sous Linux.

## Contenu d'une archive publiée

Chaque archive finale contient :

- l'application et ses bibliothèques ;
- `LISEZ-MOI.txt` avec les instructions de lancement ;
- `GUIDE_PROFESSEUR.md` ;
- `LICENSE` ;
- `THIRD_PARTY_NOTICES.md` ;
- `CITATION.cff`.

## Publication GitHub

Le workflow `.github/workflows/release.yml` est déclenché par un tag `v*`. Il :

1. vérifie que le tag correspond à la version de `pyproject.toml` ;
2. vérifie `uv.lock` et exécute les tests ;
3. construit le paquet portable Windows et les bundles macOS/Linux ;
4. vérifie la signature du runtime Windows ;
5. calcule une empreinte SHA-256 ;
6. joint les archives et les empreintes à la GitHub Release.

Aucun compte Azure, certificat payant ou secret de signature n'est nécessaire.

Exemple :

```bash
git tag -a v2.0.1 -m "FieldLab 2.0.1"
git push origin v2.0.1
```

Ne créez le tag qu'après validation du commit sur lequel il pointe.

## Pièges connus

- **Windows/VTK** : l'édition portable Windows 2.0.1 est volontairement limitée
  à la 2D afin d'éviter les DLL VTK refusées par Smart App Control.
- **Linux/OpenGL** : la machine de build a besoin de `libGL`, `libEGL` et
  `libGLU`.
- **Plugins Qt** : les plugins natifs de la plateforme doivent rester dans le
  paquet.
- **macOS** : `FieldLab.app` n'est ni signé ni notarifié. Gatekeeper demandera
  une confirmation au premier lancement.
- **Licences** : conserver `THIRD_PARTY_NOTICES.md` avec chaque archive.

## Test à froid obligatoire avant diffusion

Sur une machine sans Python :

1. télécharger l'archive depuis le même lien que les destinataires ;
2. vérifier son SHA-256 puis la décompresser entièrement ;
3. lancer `FieldLab.exe` et confirmer l'absence de blocage Windows ;
4. ouvrir un scénario 2D dans chacun des trois domaines ;
5. lancer une simulation puis exporter un PNG et un MP4 ;
6. fermer puis relancer l'application.

Ce test manuel reste nécessaire même si la construction et les tests automatisés
réussissent.
