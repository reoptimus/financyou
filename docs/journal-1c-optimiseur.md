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
- **Statut** : réglé le 2026-10-07 (étape 1.C.3) : `min_bond_allocation` ne borne
  plus que `bond` et `max_equity_allocation` que `stock`. Sur le pipeline
  d'exemple, l'immobilier n'est plus forcé à 5 % (il tombe à 0).
- **Constat** : `_run_optimization` transforme `min_bond_allocation` en poids
  minimal de **chaque** actif et `max_equity_allocation` en poids maximal de
  **chaque** actif. Sur le pipeline d'exemple, l'immobilier est ainsi forcé à
  5 % au minimum sans raison, et les obligations ne sont pas réellement
  garanties à 5 %. La frontière efficiente, elle, ignore ces contraintes.

## 5. Ratio de Sharpe calculé sans taux sans risque — réglé

- **Ouvert le** : 2026-10-06 (étape 1.C.1)
- **Statut** : réglé le 2026-10-06 (étape 1.C.2) : le Sharpe et l'objectif
  `max_sharpe` utilisent le rendement excédentaire sur la moyenne de
  `interest_rate`, exposée dans `optimal_portfolio['risk_free_rate']`. Sur le
  pipeline d'exemple, la part actions passe de 20 % à 35 %.
- **Constat** : `sharpe_ratio` vaut rendement / volatilité, sans soustraire
  de taux sans risque, et l'objectif `max_sharpe` maximise cette quantité.
  L'interface l'affiche sous le nom « Sharpe Ratio ». Le taux sans risque est
  disponible dans les scénarios (`interest_rate`).

## 6. Chiffres factices retirés ou calculés (étape 1.C.2)

- **Ouvert et réglé le** : 2026-10-06
- **Statut** : réglé
- **Calculé réellement** : `real_wealth` (patrimoine déflaté par l'inflation
  du scénario, il valait le nominal) ; `volatility_sensitivity` (effet d'une
  hausse de 10 % de la volatilité de chaque actif) ; les constats du résumé
  (probabilité d'atteindre l'objectif, perte maximale médiane). Le résumé
  affirmait « strong probability of goal achievement » quel que soit le
  résultat ; sur le pipeline d'exemple, la probabilité réelle est de 1 %.
- **Retiré** : la cascade fiscale (`tax_impact_waterfall`, liste littérale) ;
  les soldes par compte du moteur fiscal (tous à 0) ; les « conseils »
  fiscaux (séquence de retrait figée, conversion Roth, récolte de pertes) ;
  `rebalancing_schedule` (DataFrame vide, reviendra avec les coûts de
  transaction en 1.C.4) ; `correlation_sensitivity` et `years_to_goal`
  (vides) ; `probability_of_success` et `shortfall_risk` des statistiques
  (0 en dur, la probabilité vit dans `goal_analysis`).
- **Test de garde** : `tests/test_display_outputs.py` échoue si une sortie de
  l'optimiseur, du moteur fiscal ou du rapport est vide ou constante.

## 7. Documentation d'architecture décrivant l'ancienne API

- **Ouvert le** : 2026-10-06 (étape 1.C.2)
- **Statut** : ouvert
- **Constat** : `ARCHITECTURE.md`, `MODULES_GUIDE.md` et `COMPLETE_GUIDE.md`
  décrivent encore les sorties retirées au point 6. Ce sont des documents
  pour développeurs, pas des écrans utilisateur ; à réécrire avec le parcours
  unique de la phase 2.1.

## 8. Montants en euros affichés avec le symbole « $ »

- **Ouvert le** : 2026-10-06 (étape 1.C.2)
- **Statut** : ouvert, à traiter en phase 2.1 (parcours en français)
- **Constat** : le rapport et les exemples formatent les montants avec `$`
  alors que la seule devise validée est l'euro.

## 9. Rééquilibrage et coûts de transaction appliqués (étape 1.C.4)

- **Ouvert et réglé le** : 2026-10-06
- **Statut** : réglé
- **Avant** : chaque scénario était simulé avec des poids constants,
  c'est-à-dire un rééquilibrage continu et gratuit ; `transaction_costs`
  et `rebalancing_threshold` n'étaient lus nulle part.
- **Après** : le portefeuille dérive, il est ramené à la cible en fin d'année
  quand un poids s'écarte de plus de `rebalancing_threshold`, et les coûts
  sont prélevés sur le montant échangé. `simulation_results` expose de
  nouveau un `rebalancing_schedule`, désormais calculé (part des scénarios
  rééquilibrés, rotation moyenne, coût moyen par année), et le coût total par
  scénario. La simulation est vectorisée sur les scénarios.
- **Bug corrigé au passage** : la mise initiale était comptée deux fois et
  chaque versement décalé d'un an (`net_flow[t]` ajouté en fin d'année
  `t+1`). La mise initiale par défaut de 10 000, inventée, est remplacée
  par une erreur explicite quand la série de flux manque.
- **Écart sur le pipeline d'exemple** (médiane du patrimoine final,
  1 000 scénarios) : 1 300 565 → 1 352 136. Décomposition : calendrier des
  versements +49 000, rééquilibrage à seuil 5 % au lieu de continu +3 100,
  coûts de transaction −500 (coût moyen 350 sur 30 ans).

## 10. Coûts de transaction et seuil de rééquilibrage non sourcés

- **Ouvert le** : 2026-10-06 (étape 1.C.4)
- **Statut** : à trancher par l'utilisateur
- **Constat** : les valeurs par défaut (actions 0,10 %, obligations 0,05 %,
  immobilier 0,20 % du montant échangé ; seuil 5 %) sont des littéraux de
  `optimizer.py`. Ce sont des hypothèses de marché, au même titre que celles
  de `market_assumptions/default-2026.json`, qui est un fichier validé.
- **Proposition** : les verser dans un millésime suivant de
  `market_assumptions`, sourcés (frais de courtage et spreads d'un courtier
  en ligne type), avec votre validation. Un coût immobilier de 0,20 % est
  sans rapport avec les frais réels d'une transaction immobilière directe
  (frais de notaire de l'ordre de 7 à 8 % dans l'ancien), et pertinent
  seulement pour un support immobilier coté.

## 11. Performance : 1 000 scénarios × 30 ans (étape 1.C.5)

- **Ouvert et réglé le** : 2026-10-06
- **Statut** : réglé
- **Mesure** (fiscalité + optimisation, scénarios stochastiques EUR, même
  machine) : `main` 14,0 s (fiscalité 9,5 s, optimiseur 4,6 s) ; après
  1.C.4 (simulation vectorisée) 10,2 s ; après 1.C.5 (tables fiscales
  vectorisées) 0,2 s.
- **Correction** : `_calculate_tax_tables` bouclait par scénario puis par
  ligne (`iterrows`). Le calcul vectorisé produit des tableaux identiques à
  l'ancien, vérifié sur 200 scénarios × 30 ans.
- **Test de garde** : `tests/test_performance.py`, budget de 5 s.

## 12. Contraintes par enveloppe (étape 1.C.3)

- **Ouvert et réglé le** : 2026-10-07
- **Statut** : réglé, avec une limite déclarée (ci-dessous)
- **Décision de seb** : l'indice actions des scénarios est éligible au PEA,
  dans la limite du plafond de versements (150 000 €, régime `fr-2026`).
- **Après** : l'optimiseur accepte `wrapper_constraints` (pays, millésime,
  enveloppes ouvrables). Éligibilité et plafonds viennent du régime, jamais du
  code. Un plafond ne borne pas seul un actif tant qu'une enveloppe sans
  plafond (CTO, assurance-vie) peut le détenir : la condition de réalisabilité
  (Hall, sur tous les sous-ensembles d'actifs) devient des inégalités
  linéaires sur les poids. Un cas impossible (par exemple PEA seul pour
  1 M€ de versements) lève une erreur française explicite. La frontière
  efficiente respecte les mêmes contraintes.
- **Sortie** : `wrapper_allocation` (actif, enveloppe, part des versements,
  montant). Sur le pipeline d'exemple, le PEA reçoit exactement 150 000 €.
- **Limite** : le placement est **réalisable, pas optimisé fiscalement**
  (heuristique : enveloppes plafonnées d'abord). Le moteur fiscal calcule
  encore l'après-impôt avec les anciens comptes taxable / différé / exonéré :
  les rendements après impôt ne dépendent pas de l'enveloppe. Un moteur fiscal
  par enveloppe est la suite logique.

## 13. Impôt de sortie par enveloppe (étape 1.D.1)

- **Ouvert le** : 2026-10-07
- **Statut** : première brique livrée, intégration à l'optimiseur ouverte (1.D.2)
- **Livré** : `investment_calculator/wrapper_tax.py::liquidation_tax` calcule
  l'impôt dû à la liquidation totale d'une enveloppe à partir de la règle de
  retrait du régime (taux, taux social, abattement, seuil de primes). Pris en
  charge : CTO, PEA, assurance-vie, Livret A. Aucun taux dans le code.
- **Refusé explicitement** (`NotImplementedError`) : PER (barème et déduction à
  l'entrée) et immobilier direct (revenus fonciers annuels, abattements pour
  durée de détention).
- **Choix de modélisation à faire valider par un fiscaliste** : liquidation
  totale à l'horizon ; durée de détention depuis l'ouverture ; pas d'imputation
  des moins-values ; assurance-vie au-dessus du seuil de primes, plus-value
  répartie au prorata des primes sous et au-dessus du seuil ; abattement imputé
  d'abord sur la fraction au taux le plus bas (hypothèse prudente, non
  confrontée à la doctrine).
- **Reste ouvert** : prélèvements sociaux à 18,6 % (journal fiscalité, à
  trancher par seb) : ce module reprend le taux du régime tel quel.
- **Suite (1.D.2)** : l'optimiseur simule chaque enveloppe comme une poche
  distincte sur les rendements avant impôt, y applique l'impôt annuel des
  enveloppes imposées au fil de l'eau et `liquidation_tax` à l'horizon. Sans
  cela, appliquer l'impôt de sortie sur des rendements déjà après impôt
  (moteur fiscal historique) compterait l'impôt deux fois.
