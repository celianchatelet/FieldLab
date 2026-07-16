# Validation scientifique et limites

FieldLab est conçu pour l'enseignement et l'exploration numérique. La validation
automatisée cherche à détecter les erreurs d'unités, de signe, d'échelle et de
discrétisation les plus importantes ; elle ne constitue pas une certification.

## Contrôles automatisés actuels

### Électrostatique

- Un condensateur plan retrouve `E = ΔV/d` à moins de 1 % dans la zone centrale.
- Une densité volumique de charge est mise à l'échelle par `ε₀` et comparée à la
  solution analytique 1D d'une plaque chargée.
- Le diélectrique partiel utilise la permittivité relative définie pour le
  matériau sélectionné.

### Magnétostatique

- Le champ 2D d'un fil long est comparé à `B(r) = μ₀I/(2πr)` avec une tolérance
  de 5 % liée à la discrétisation.
- L'intégration 3D de Biot–Savart sur un segment très long retrouve la même loi
  avec une erreur relative inférieure à `10⁻⁴` dans le test de référence.
- Les coefficients magnétiques du fond et des matériaux sont contrôlés dans le
  modèle 2D.

### Thermique

- Les temps caractéristiques sont calculés à partir de la diffusivité
  `α = κ/(ρcp)` en unités SI.
- La diffusion transitoire 1D dans l'eau est comparée à une solution analytique
  en série de Fourier.
- Le scénario de trempe vérifie que l'objet chaud refroidit sans rester soumis à
  une température artificiellement imposée.
- Le mur composite contrôle l'utilisation des conductivités thermiques des deux
  matériaux.

### Interface et exports

- Le mode Cours masque les paramètres experts et conserve des valeurs sûres.
- L'échantillonnage des sondes 2D est vérifié sur un champ affine connu.
- Les exports PNG sont contrôlés à la résolution demandée et les animations
  reçoivent un horodatage.

## Reproduire les contrôles

```bash
uv sync --extra dev
uv run pytest -q
```

Les tests de physique principaux se trouvent dans
`tests/test_electromagnetisme_si.py` et `tests/test_thermique_physique.py`.

## Limites à annoncer avec les résultats

- Les résultats dépendent du maillage, du domaine tronqué et des conditions aux
  limites. Une étude de convergence reste nécessaire.
- Les modèles 2D supposent une invariance dans la direction hors plan.
- Le thermique fluide ne résout ni l'écoulement ni la convection naturelle.
- Le magnétisme 3D est calculé dans le vide par Biot–Savart ; il ne modélise pas
  l'effet d'un noyau ferromagnétique.
- Les propriétés de matériaux sont des valeurs pédagogiques représentatives et
  peuvent varier avec la température, la fréquence, la pureté ou le fournisseur.

Pour un usage de recherche ou d'ingénierie, comparez les résultats à une
solution analytique, à un logiciel de référence ou à une mesure expérimentale.
