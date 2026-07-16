# Contribuer à FieldLab

Merci de contribuer à FieldLab. Les corrections de modèles physiques, les
nouveaux scénarios pédagogiques, les tests et les améliorations de documentation
sont particulièrement utiles.

## Préparer l'environnement

FieldLab utilise Python 3.10 ou plus récent et `uv` pour verrouiller les
dépendances.

```bash
git clone https://github.com/celianchatelet/FieldLab.git
cd FieldLab
uv sync --extra dev
```

Lancer l'application :

```bash
uv run fieldlab
```

## Vérifications obligatoires

Avant de proposer une modification :

```bash
uv run ruff check --select E9,F63,F7,F82 fieldlab tests main.py
uv run pytest -q
```

Une modification d'un modèle physique doit inclure au moins un test comparant le
résultat à une solution analytique, une loi d'échelle, une conservation ou une
référence numérique clairement documentée. Précisez les unités, les hypothèses
et la tolérance choisie.

## Proposition de modification

- Limitez chaque proposition à un objectif cohérent.
- Décrivez le comportement avant et après la modification.
- Ajoutez ou mettez à jour les tests et la documentation concernés.
- Ne joignez pas les dossiers générés `build/`, `dist/` ou les environnements
  virtuels.
- Pour un changement visible dans l'interface, joignez une capture d'écran.

En signalant un défaut scientifique, indiquez le scénario, les paramètres, la
valeur obtenue, la valeur attendue et la source de référence utilisée.
