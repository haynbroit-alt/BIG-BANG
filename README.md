# BIG BANG

**Universe as Code — un studio de compilation d'applications.**

BIG BANG n'est pas un générateur de code. Vous décrivez votre *univers*
(entités, rôles, flux, monétisation) dans un seul fichier `genesis.yaml`, et
BIG BANG le compile en une application complète — backend, frontend, Docker,
documentation — qu'il sait ensuite **valider, mettre à jour et documenter**
au fil de vos changements, sans écraser vos modifications.

## Démarrage rapide

```bash
pip install -e .
big-bang bang examples/api_minimal.yaml --output ./mon-projet
```

À la première exécution, tous les fichiers sont générés. Aux exécutions
suivantes, seuls les blocs gérés sont régénérés — vos modifications sont
préservées (`--force` pour tout écraser, `--dry-run` pour prévisualiser).

## Comment ça marche

```
genesis.yaml → parser → Universe IR → résolveur → plugins → émetteurs → application
```

- **Parser & DSL** (`bigbang/parser.py`) — lit et valide `genesis.yaml`.
- **IR** (`bigbang/ir.py`) — représentation intermédiaire en graphe de l'univers.
- **Résolveur** (`bigbang/resolver.py`) — analyse sémantique, diagnostics.
- **Plugins** (`bigbang/plugins/`) — transformations pures de l'IR (auth, backend, frontend, docker, docs…).
- **Émetteurs** (`bigbang/emitters/`) — écrivent les fichiers (FastAPI, frontend, Docker, docs).
- **Compilation incrémentale** (`bigbang/differ.py`, `bigbang/merger.py`) — merge par blocs, éditions utilisateur préservées.

## Exemples

Voir [`examples/`](examples/) : une API minimale et un SaaS CRM complet.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

La suite couvre le parser, le résolveur, le merger, le pipeline de bout en
bout (y compris le déterminisme octet par octet des sorties) et le CLI. Elle
tourne en CI à chaque push.

## Vision, stratégie & feuille de route

- [`VISION.md`](VISION.md) — ce que BIG BANG est, ses quatre principes non
  négociables, l'architecture cible Core / CLI / Studio / SDK.
- [`docs/STRATEGY.md`](docs/STRATEGY.md) — l'ordre des chantiers.
