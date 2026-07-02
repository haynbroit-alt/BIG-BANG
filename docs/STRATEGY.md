# BIG BANG — Stratégie & Feuille de route

> **BIG BANG n'est pas un « générateur de code ». C'est un studio de compilation d'applications.**
>
> L'utilisateur travaille toujours au niveau de son *univers* (`genesis.yaml`) ;
> BIG BANG s'occupe de générer, valider, mettre à jour et documenter
> automatiquement l'application. C'est cette expérience cohérente — plus que la
> quantité de fonctionnalités — qui fait la différence.

## Principe directeur

La qualité ne vient pas du fait de travailler plus, mais de travailler **dans
le bon ordre**. Cinq fonctionnalités bien finies valent mieux que cinquante
incomplètes.

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
| **Tests automatisés** | — | ❌ **Absents** |
| **Documentation** | `README.md` (1 ligne) | ❌ **Absente** |
| Interface graphique (studio) | — | ⬜ Pas commencée |

Conclusion : l'architecture du cœur est en place, mais rien ne **prouve** sa
fiabilité, et rien ne permet à un nouvel utilisateur de l'essayer facilement.
La suite du travail découle de ce constat.

---

## Phase 1 — Un cœur extrêmement solide *(priorité absolue)*

Le compilateur est la fondation. Si le cœur est fiable, tout le reste devient
plus simple.

- [ ] **Tests automatisés** — c'est le chantier n°1, car il n'en existe aucun :
  - tests unitaires : parser, résolveur, IR builder, differ, merger ;
  - *golden tests* : compiler `examples/*.yaml` et comparer les sorties à des
    instantanés de référence ;
  - test de déterminisme : deux compilations du même `genesis.yaml` doivent
    produire des sorties strictement identiques (octet par octet) ;
  - CI GitHub Actions qui exécute tout à chaque push.
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
