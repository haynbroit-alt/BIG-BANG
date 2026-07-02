# BIG BANG — Stratégie & Feuille de route

> La vision du projet — ce que BIG BANG *est*, ses quatre principes non
> négociables (Offline First, Deterministic, Open Source, Extensible) et
> l'architecture cible Core / CLI / Studio / SDK — est figée dans
> [`VISION.md`](../VISION.md). Ce document-ci décrit le *comment* et
> l'*ordre* ; il évolue, la vision non.

## Principe directeur

La qualité ne vient pas du fait de travailler plus, mais de travailler **dans
le bon ordre**. Cinq fonctionnalités bien finies valent mieux que cinquante
incomplètes.

## Décision en vigueur : consolidation avant fonctionnalités

Le projet a changé de catégorie : parti comme générateur CRUD, c'est
aujourd'hui un compilateur d'applications. Ce qui distingue un projet
expérimental d'un projet utilisé par d'autres, c'est l'étape la moins
visible. **Gel des fonctionnalités** jusqu'à la fin de la phase 1 : on écrit
les tests, on écrit la documentation, on nettoie les API, on améliore les
messages d'erreur, on stabilise le DSL — rien d'autre.

---

## État actuel (v0.5)

Ce qui existe déjà dans le dépôt :

| Composant | Fichiers | État |
|---|---|---|
| Parser DSL | `bigbang/parser.py` | ✅ Fonctionnel |
| IR (Universe IR + graphe) | `bigbang/ir.py`, `bigbang/ir_builder.py` | ✅ Fonctionnel |
| Résolveur sémantique | `bigbang/resolver.py` | ✅ Fonctionnel |
| Pipeline multi-passes | `bigbang/pipeline.py` | ✅ Fonctionnel |
| Plugins (transformations pures) | `bigbang/plugins/` (auth, backend, frontend, docker, docs, ed25519) | ✅ Fonctionnel |
| Émetteurs | `bigbang/emitters/` (fastapi, frontend, docker, docs) | ✅ Fonctionnel |
| Diff incrémental / merge par blocs | `bigbang/differ.py`, `bigbang/merger.py`, `bigbang/snapshot.py` | ✅ Fonctionnel |
| Diagnostics | `bigbang/diagnostics.py` | ✅ Fonctionnel |
| CLI (`big-bang bang`) | `bigbang/cli.py` | ✅ Fonctionnel |
| Tests automatisés | `tests/` (34 tests : parser, resolver, merger, pipeline, CLI) | 🟡 Démarrés — à étendre |
| CI | `.github/workflows/ci.yml` (pytest, Python 3.10 & 3.12) | ✅ Fonctionnelle |
| Documentation | `README.md`, `VISION.md`, `docs/STRATEGY.md` | 🟡 Démarrée |
| Interface graphique (studio) | — | ⬜ Pas commencée |

Conclusion : l'architecture du cœur est en place, mais rien ne **prouve** sa
fiabilité, et rien ne permet à un nouvel utilisateur de l'essayer facilement.
La suite du travail découle de ce constat.

---

## Phase 1 — Un cœur extrêmement solide *(priorité absolue)*

Le compilateur est la fondation. Si le cœur est fiable, tout le reste devient
plus simple.

- [x] **Tests automatisés — socle** (`tests/`, 34 tests) :
  - tests unitaires : parser, résolveur, merger ;
  - chaque exemple de `examples/` compile sans erreur ;
  - test de déterminisme : deux compilations du même `genesis.yaml`
    produisent des sorties identiques octet par octet — **vérifié, ça tient
    déjà**, à l'exception connue de `.bigbang.lock` (horodatage
    `generated_at`, dette à résorber) ;
  - les éditions utilisateur hors blocs survivent à la recompilation ;
  - CI GitHub Actions à chaque push et pull request.
- [ ] **Tests à étendre** — IR builder, differ, plugins individuels,
  *golden tests* comparant les sorties à des instantanés de référence ;
  supprimer l'horodatage de `.bigbang.lock` pour un déterminisme total.
- [ ] **Messages d'erreur** — chaque diagnostic doit dire quoi corriger et
  où (`path` + `hint` systématiques).
- [ ] **DSL stable** — spécification versionnée de `genesis.yaml`
  (`schema_version`), avec un JSON Schema publié qui sert à la fois à la
  validation et, plus tard, à l'autocomplétion dans les éditeurs.
- [ ] **IR bien définie** — documenter le contrat de l'IR (nœuds, graphe,
  invariants) ; toute évolution passe par une entrée de changelog.
- [ ] **Pipeline déterministe** — aucun horodatage, aucun ordre de dict
  non trié, aucun aléa dans les fichiers émis.
- [ ] **Plugins propres** — API `BangPlugin` documentée et figée : entrées
  (IR), sorties (transformations pures), déclaration de dépendances.

**Critère de sortie :** CI verte, couverture du cœur, compilation reproductible.

## Phase 2 — Une interface simple au début

Ne pas construire une interface sophistiquée trop tôt. Le studio v1 se limite
à **cinq fonctionnalités bien finies** :

1. un écran **« Nouveau projet »** ;
2. un **éditeur YAML** ;
3. un bouton **Compiler** ;
4. un panneau **Diagnostics** (réutilise `bigbang/diagnostics.py`) ;
5. un **aperçu des fichiers générés**.

Rien d'autre en v1. Chaque écran doit être irréprochable avant d'en ajouter un.

## Phase 3 — Une excellente documentation

Un bon projet se juge à la facilité avec laquelle un nouvel utilisateur peut
l'essayer.

- [ ] **Tutoriel de 5 minutes** : installation → premier `genesis.yaml` →
  `big-bang bang` → application qui tourne.
- [ ] **Galerie d'exemples** : enrichir `examples/` (API minimale, SaaS CRM,
  blog, e-commerce…), chacun compilant sans erreur (vérifié en CI).
- [ ] **Documentation des plugins** : comment en écrire un, contrat de l'API,
  exemple complet commenté.
- [ ] **Architecture expliquée avec des schémas** : le voyage d'un
  `genesis.yaml` à travers parser → IR → résolveur → plugins → émetteurs.

## Phase 4 — Une identité visuelle cohérente

- Interface **moderne mais sobre** ;
- **modes clair et sombre** dès le départ ;
- **peu de couleurs d'accent** (une couleur primaire, états succès/erreur) ;
- icônes simples et cohérentes.

L'objectif : que le développeur se concentre sur son univers, pas sur
l'interface.

## Phase 5 — Des fonctionnalités qui apportent une vraie valeur

Ce sont ces fonctions qui différencient BIG BANG, pas une interface chargée :

- [ ] **Validation du DSL en temps réel** (le JSON Schema de la phase 1 rend
  cela presque gratuit) ;
- [ ] **Autocomplétion pour `genesis.yaml`** (même schéma, exposé aux éditeurs
  via yaml-language-server) ;
- [ ] **Aperçu graphique des entités** (le graphe IR existe déjà — il suffit de
  le rendre visuellement) ;
- [ ] **Pipeline transparent** — faire de l'IR une fonctionnalité visible, pas
  seulement interne : dans le Studio, l'utilisateur explore chaque étape
  (Parser → IR → Resolver → Plugins → Emitters), comprend pourquoi une
  relation a été inférée, voit quels plugins ont enrichi l'IR, et inspecte le
  résultat avant même la génération des fichiers ;
- [ ] **Compilation incrémentale** (fondations déjà en place :
  `differ.py`, `snapshot.py` — à exposer et à optimiser) ;
- [ ] **Comparaison entre deux versions d'un univers** (diff sémantique au
  niveau IR : « l'entité *Site* a gagné le champ *status* », pas un diff texte).

## Phase 6 — Une expérience utilisateur fluide

Le parcours de référence, à rendre rapide et fiable de bout en bout :

1. créer un projet ;
2. écrire quelques lignes de YAML ;
3. cliquer sur **Compiler** (ou `big-bang bang`) ;
4. voir immédiatement les diagnostics et les fichiers générés ;
5. lancer l'application **en une seule commande**.

Si ce parcours est rapide et fiable, le projet donne une impression de
qualité. Ce parcours est le test d'acceptation permanent du projet : chaque
release doit le rejouer intégralement.

---

## Ce qu'on ne fait *pas* (pour l'instant)

- Pas d'interface sophistiquée avant que le cœur soit prouvé fiable (phase 1).
- Pas de nouvelles cibles d'émission (autres frameworks) avant la stabilisation
  du DSL et de l'IR.
- Pas de fonctionnalités « vitrines » qui n'améliorent pas le parcours de
  référence de la phase 6.
