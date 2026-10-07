# Journal — chantier 1.C (optimiseur et vérité des chiffres)

Même convention que `docs/journal-fiscalite.md` : tout ce qui a été identifié
mais volontairement pas réglé dans l'étape en cours. Statuts : `ouvert`,
`à trancher par l'utilisateur`, `réglé`. Rien n'est retiré ; une entrée réglée
est marquée comme telle.

---

## 1. Covariance estimée sur des moyennes par scénario — réglé

- **Ouvert et réglé le** : 2026-10-06 (étape 1.C.1)
- **Statut** : réglé
- **Constat** : `_extract_asset_returns` moyennait les 30 pas de temps de
  chaque scénario avant d'estimer la covariance. Sur le pipeline d'exemple
  (1 000 scénarios × 30 ans, graine 42), la volatilité des actions après impôt
  passait de 13,7 % (rendements annuels) à 2,6 % (moyennes par scénario),
  soit un facteur 5,3 ≈ √30.
- **Correction** : les moments sont estimés sur les rendements périodiques.
  La perte maximale, qui était calculée sur la suite des moyennes de
  scénarios (et valait 0), est désormais la médiane des pertes maximales
  calculées scénario par scénario.
- **Pourquoi l'allocation a peu bougé** : diviser toute la covariance par un
  même facteur ne change pas le portefeuille de Sharpe maximal. Ce sont les
  chiffres de risque affichés qui étaient faux (volatilité 0,8 %, Sharpe 6,9),
  pas tant la répartition.

## 2. Scénarios à pas infra-annuel refusés par l'optimiseur

- **Ouvert le** : 2026-10-06 (étape 1.C.1)
- **Statut** : ouvert
- **Constat** : le chemin stochastique du générateur produit des rendements
  de période, le chemin simple des rendements annualisés quel que soit
  `timestep`. Annualiser dans l'optimiseur serait juste pour l'un et faux pour
  l'autre.
- **Décision provisoire** : l'optimiseur lève une `ValueError` explicite si le
  pas n'est pas annuel. Aucun appelant actuel (exemples, interface) n'utilise
  un autre pas.
- **À reprendre** : harmoniser la sémantique des rendements entre les deux
  chemins du générateur (périmètre 1.B), puis annualiser dans l'optimiseur.

## 3. Le chemin simple du générateur a une covariance singulière

- **Ouvert le** : 2026-10-06 (étape 1.C.1)
- **Statut** : ouvert, hors périmètre 1.C
- **Constat** : `ScenarioGenerator._generate_simple` construit actions,
  obligations et immobilier à partir de deux chocs seulement
  (`market_shock`, `base_shock`). La matrice de covariance des trois actifs
  est donc de rang 2 (plus petite valeur propre ~1e-18) : il existe une
  combinaison d'actifs sans risque, artefact du générateur.
- **Effet** : le portefeuille de variance minimale n'est pas garanti unique
  sur ces scénarios. Les tests de propriété de la frontière utilisent le
  chemin stochastique.
- **À reprendre** : ajouter un choc propre à chaque actif dans le chemin
  simple (périmètre 1.B, change les chiffres du chemin simple).

## 4. Contraintes utilisateur appliquées à tous les actifs

- **Ouvert le** : 2026-10-06 (étape 1.C.1)
- **Statut** : ouvert, à traiter en 1.C.3 (contraintes)
- **Constat** : `_run_optimization` transforme `min_bond_allocation` en poids
  minimal de **chaque** actif et `max_equity_allocation` en poids maximal de
  **chaque** actif. Sur le pipeline d'exemple, l'immobilier est ainsi forcé à
  5 % au minimum sans raison, et les obligations ne sont pas réellement
  garanties à 5 %. La frontière efficiente, elle, ignore ces contraintes.

## 5. Ratio de Sharpe calculé sans taux sans risque

- **Ouvert le** : 2026-10-06 (étape 1.C.1)
- **Statut** : ouvert, à traiter en 1.C.2 (vérité des chiffres)
- **Constat** : `sharpe_ratio` vaut rendement / volatilité, sans soustraire
  de taux sans risque, et l'objectif `max_sharpe` maximise cette quantité.
  L'interface l'affiche sous le nom « Sharpe Ratio ». Le taux sans risque est
  disponible dans les scénarios (`interest_rate`).
