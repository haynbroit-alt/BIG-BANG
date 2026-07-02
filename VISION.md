# BIG BANG — Vision

> **BIG BANG transforme une description déclarative d'un univers numérique en
> une application complète, déterministe et extensible.**

Ce document est volontairement court et stable. Il ne décrit pas *comment*
construire BIG BANG (voir [`docs/STRATEGY.md`](docs/STRATEGY.md)) mais *ce que
BIG BANG est* — et il ne changera presque plus. Toute décision future doit
être compatible avec ce qui suit.

## Ce que BIG BANG est

Un **compilateur d'applications**, pas un générateur CRUD. L'utilisateur
travaille toujours au niveau de son univers (`genesis.yaml`) ; BIG BANG
compile cet univers à travers un pipeline explicite :

```
genesis.yaml → Parser → IR → Resolver → Plugins → Emitters → Projet généré
```

Chaque étape a un contrat clair, et chaque étape est **inspectable** : l'IR
n'est pas un détail interne mais une surface visible du produit. L'utilisateur
peut explorer le graphe, comprendre pourquoi une relation a été inférée, voir
quels plugins ont enrichi l'IR, et inspecter le résultat avant même la
génération des fichiers. Peu d'outils rendent leur compilation aussi
transparente — c'est le différenciateur de BIG BANG.

## Quatre principes non négociables

1. **Offline First** — BIG BANG fonctionne sans Internet. La compilation ne
   dépend d'aucun service distant.
2. **Deterministic** — même DSL → même sortie, octet par octet. Pas
   d'horodatage, pas d'aléa, pas d'ordre d'itération non défini dans les
   fichiers émis.
3. **Open Source** — aucune dépendance propriétaire dans le cœur. Le
   compilateur reste librement auditable et utilisable de bout en bout.
4. **Extensible** — toutes les fonctionnalités avancées passent par des
   plugins (transformations pures de l'IR) et des émetteurs. Ajouter une cible
   ne modifie jamais le cœur.

Une proposition qui viole l'un de ces principes est refusée, quelle que soit
sa valeur apparente.

## Architecture cible : trois produits, un seul cœur

```
BIG BANG Core   ← le compilateur, sans interface
      │
      ├── CLI      ← développeurs et pipelines CI/CD
      ├── Studio   ← interface graphique
      └── SDK      ← intégrer BIG BANG dans d'autres outils (Python)
```

Une seule logique de compilation est maintenue ; elle est utilisable dans
plusieurs contextes. Le Core ne connaît ni le terminal, ni le navigateur : il
prend un univers en entrée et rend un `CompilationResult` structuré
(diagnostics, graphe, fichiers). CLI, Studio et SDK ne sont que des vues sur
ce résultat.

## Ce qui distingue BIG BANG

Pas la quantité de fonctionnalités, mais **la cohérence et la fiabilité** :
un cœur stable, des contrats clairs, une expérience utilisateur simple, et
une compilation transparente que l'utilisateur peut comprendre étape par
étape.
