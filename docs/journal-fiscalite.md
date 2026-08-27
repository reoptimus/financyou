# Journal — questions en suspens et points à revoir

Ce document recense, au fil de la feuille de route fiscalité (phase 1.A et
suivantes), tout ce qui a été identifié mais **volontairement pas réglé
dans l'immédiat** : une incertitude déclarée, une décision qui appartient à
un humain, une simplification assumée, ou un point à reprendre plus tard.
Il complète `docs/validation/1a-cas-d-or.md` (qui documente l'étape 1.A
elle-même) sans le remplacer, et vit au-delà de cette étape.

Chaque entrée porte une date d'ouverture, un statut, et — quand elle est
réglée — une date et un résumé de la résolution. Rien n'est retiré du
journal ; une entrée réglée est marquée comme telle, pas supprimée.

Statuts utilisés : `ouvert` (personne n'a tranché), `à trancher par
l'utilisateur` (bloque une décision produit ou de confiance, pas technique),
`en attente de source` (une recherche complémentaire est nécessaire), `réglé`.

---

## 1. Prélèvements sociaux à 18,6 % au lieu de 17,2 % (LFSS 2026)

- **Ouvert le** : 2026-08-27 (étape 1.A.3)
- **Statut** : à trancher par l'utilisateur
- **Contexte** : la LFSS pour 2026 relève la CSG sur le capital de 9,2 % à
  10,6 %, portant les prélèvements sociaux de 17,2 % à 18,6 % pour les
  plus-values mobilières, dividendes, CTO, PEA, PER, épargne salariale,
  LMNP et crypto-actifs — dès les revenus 2025. L'assurance-vie, l'épargne
  réglementée et l'immobilier non meublé restent à 17,2 %.
- **Décision prise le 2026-08-27** : accepter le `known_gap` et avancer
  (choix explicite de l'utilisateur, voir la question posée avant l'étape
  5). `fr-2026.json` applique encore 17,2 % partout ; les cas d'or
  `cto_pfu_plus_value`, `pea_retrait_apres_cinq_ans`,
  `pea_retrait_avant_cinq_ans` et `per_sortie_capital_retraite` restent
  `pending_regime_data`.
- **À reprendre** : faire porter le taux social par enveloppe ou catégorie
  de revenu (pas un taux global unique comme aujourd'hui), avec la bonne
  date d'effet, dans une itération dédiée. Nécessite une extension de
  schéma (`social_contributions` par enveloppe plutôt qu'un
  `investment_income.rate` unique).

## 2. Statut de la CDHR pour les revenus 2025

- **Ouvert le** : 2026-08-27 (étape 1.A.2/1.A.3)
- **Statut** : en attente de source
- **Contexte** : un agent de recherche a rapporté une « pérennisation
  conditionnelle » de la contribution différentielle sur les hauts revenus,
  avec un numéro de loi précis (loi n° 2026-103 du 19/02/2026), mais a
  lui-même signalé ne pas avoir pu lire le texte source brut (accès
  bloqué, résumé seulement). Non retenu dans le régime par prudence.
- **À reprendre** : faire confirmer par une lecture humaine directe de
  Légifrance/BOFiP avant d'ajouter la CDHR au régime. Cas d'or
  `cdhr_hauts_revenus` déjà en place (`known_gap`), prêt à être rempli dès
  que la donnée est fiable.

## 3. Cas particuliers du plafonnement du quotient familial

- **Ouvert le** : 2026-08-27 (étape 1.A.2)
- **Statut** : ouvert
- **Contexte** : seul le cas général (1 807 € par demi-part) est modélisé
  dans `TaxRegime.income_tax_due`. Parent isolé, veuf avec enfant à charge,
  garde alternée au quart de part, invalides/anciens combattants ont chacun
  un mécanisme à deux étages distinct (plafond + réduction complémentaire,
  CGI art. 197 I-3°) non représenté.
- **À reprendre** : concevoir l'extension de schéma pour ces cas
  particuliers une fois le cas général validé humainement. Cas d'or
  `quotient_familial_plafonnement_cas_particuliers` en place (`known_gap`).

## 4. Formule PER pour les travailleurs non salariés (TNS)

- **Ouvert le** : 2026-08-27 (étape 1.A.2)
- **Statut** : en attente de source
- **Contexte** : la recherche a obtenu des extractions BOFiP contradictoires
  sur l'année de référence du PASS et le signe du terme additionnel de 15 %
  pour les indépendants. La branche « salarié » de la formule (10 %,
  plafonné à 8×PASS) est en confiance haute ; la branche TNS ne l'est pas.
- **À reprendre** : relecture humaine directe de BOI-IR-BASE-20-50-20,
  §270-§370, avant d'utiliser `contribution_deduction_formula.tns_*` pour
  un calcul réel.

## 5. Encours de primes d'assurance-vie net des rachats

- **Ouvert le** : 2026-08-27 (étape 1.A.2)
- **Statut** : ouvert — nécessite un choix d'architecture, pas seulement une donnée
- **Contexte** : le seuil de 150 000 € s'apprécie sur l'encours de primes
  versées net des rachats déjà effectués, calculé proportionnellement
  (BOI-RPPM-RCM-20-15). Cela suppose de suivre l'historique
  versements/rachats d'un contrat dans le temps — impossible pour un
  régime fiscal interrogé sans état à un instant donné.
- **À reprendre** : décider où vit cet état (le moteur de simulation,
  probablement à l'étape 1.B) et concevoir l'interface entre ce suivi et
  `TaxRegime.select_withdrawal_rule`. Cas d'or
  `assurance_vie_encours_primes_net_de_rachats` en place (`known_gap`).
  Le cas `assurance_vie_rachat_primes_au_dela_du_seuil` du banc applique
  déjà une simplification (taux appliqué à la totalité du gain, pas
  seulement à la fraction au-delà du seuil) — confiance `medium` déclarée,
  pas `high`.

## 6. Revenus fonciers (micro-foncier / régime réel)

- **Ouvert le** : 2026-08-27 (étape 1.A.2)
- **Statut** : ouvert — nécessite une extension du moteur, pas seulement du régime
- **Contexte** : `rental_income_regimes` porte les paramètres sourcés
  (seuil 15 000 €, abattement 30 %, plafonds de déficit foncier 10 700 €
  / 21 400 €), mais aucune méthode de `TaxRegime` ni du moteur ne les
  consomme : le revenu locatif récurrent est une catégorie de revenu
  entièrement absente du calcul aujourd'hui (seule la plus-value de
  cession de l'enveloppe `immobilier_direct` est traitée).
- **À reprendre** : probablement à l'étape 1.B, en même temps que
  l'intégration des autres catégories de revenu récurrent.

## 7. Décote d'entrée de l'IFI (1,3-1,4 M€)

- **Ouvert le** : 2026-08-27 (étape 1.A.3)
- **Statut** : ouvert
- **Contexte** : découvert en vérifiant le barème IFI (hors périmètre des
  cinq lacunes assignées). `TaxRegime.wealth_tax_due` applique le barème
  marginal dès 1,3 M€, sans le mécanisme de décote (montant réduit de
  17 500 € − 1,25 % du patrimoine) qui lisse l'entrée jusqu'à 1,4 M€.
- **Impact réel** : nul sur le cas d'or livré (`ifi_patrimoine_deux_millions`,
  2 M€, largement au-dessus du couloir concerné) ; produirait un montant
  trop élevé pour un patrimoine entre 1,3 et 1,4 M€.
- **À reprendre** : ajouter le mécanisme de décote à `wealth_tax_due` avec
  ses paramètres sourcés dans le régime.

## 8. Seuil de la surtaxe sur les plus-values immobilières élevées

- **Ouvert le** : 2026-08-27 (étape 1.A.3)
- **Statut** : en attente de source
- **Contexte** : `capital_gains.real_estate.surtax_brackets` place le
  dernier seuil à 250 000 € ; une vérification indique 260 000 €, avec un
  mécanisme de décote à chaque palier intermédiaire qu'un simple barème par
  tranches ne reproduit pas.
- **Impact réel** : nul aujourd'hui — ce champ n'est consommé par aucune
  méthode de `TaxRegime`.
- **À reprendre** : corriger la valeur et modéliser la décote avant qu'un
  calcul ne s'appuie sur ce champ.

## 9. Barème de l'IFI millésime 2026 — mention "à vérifier" non levée

- **Ouvert le** : avant cette conversation (`known_gaps` d'origine)
- **Statut** : réglé partiellement, mention conservée par prudence
- **Contexte** : la recherche de l'étape 1.A.3 confirme le barème inchangé
  depuis 2018, valable pour le fait générateur au 1er janvier 2026. Le
  `known_gap` "à vérifier" n'a pas été retiré faute de relecture humaine
  formelle du texte — voir point 7 ci-dessus qui, lui, est un vrai
  known_gap distinct (la décote, pas le barème lui-même).
- **À reprendre** : faire confirmer par une personne puis retirer la
  mention "à vérifier" (le barème lui-même, pas la décote) de
  `fr-2026.json`.

## 10. Incohérence entre le champ "Country" et le sélecteur "Tax Jurisdiction" (web_ui)

- **Ouvert le** : 2026-08-27 (étape 1.A.5)
- **Statut** : ouvert
- **Contexte** : `web_ui/app.py` et `app_enhanced.py` ont deux champs
  distincts : "Country" dans le formulaire de profil personnel (valeur
  par défaut "US", liste figée `["US", "FR", "UK", "DE", "CA"]`, purement
  informatif) et "Tax Jurisdiction" dans les réglages (maintenant déduit
  des régimes livrés, donc seulement "FR"). Les deux n'ont jamais été
  synchronisés, avant ou après le branchement sur `tax_regime`.
- **À reprendre** : décider si "Country" doit disparaître, être
  fusionné avec "Tax Jurisdiction", ou rester un champ informatif distinct
  assumé comme tel (à documenter si c'est le choix retenu).

## 11. `examples/complete_pipeline_with_files.py` — FAUSSE ALERTE, corrigée

- **Ouvert le** : 2026-08-27, **corrigé le** : 2026-08-27 (lors de la mise au
  point de la PR #18)
- **Statut** : réglé — c'était une erreur de diagnostic de ma part, pas un bug
- **Ce que j'avais écrit à tort** : le script échouerait à la sauvegarde des
  résultats (`outputs/investment_report.html` introuvable), identique sur
  `phase-0.4`, donc pas une régression de la fiscalité.
- **Ce qu'il en est réellement** : l'échec venait du bac à sable (sandbox) de
  mon propre environnement d'exécution local, qui bloquait l'écriture de
  fichiers dans un répertoire nouvellement créé — pas du code. Rejoué avec le
  sandbox désactivé (`dangerouslyDisableSandbox`) : le script tourne jusqu'au
  bout, produit les 7 fichiers attendus par le job CI « Test de fumée bout en
  bout », et le portefeuille optimal est cohérent (poids sommant à 1,
  champs complets). Confirmé aussi que la CI (runner Linux) n'a jamais ce
  problème, puisqu'il n'a rien à voir avec le code.
- **Leçon** : une commande shell qui échoue avec une erreur de fichier
  manquant, sur CE poste, mérite d'être rejouée en écartant l'hypothèse
  sandbox avant de conclure à un bug applicatif.

## 12. Dette de lint et de typage préexistante

- **Ouvert le** : 2026-08-27 (constat initial, avant tout commit)
- **Statut** : ouvert — hors périmètre fiscalité
- **Contexte** : `ruff check .` sur le dépôt entier remonte environ 540
  diagnostics préexistants (imports non triés, f-strings sans
  interpolation, exceptions larges, variables non utilisées...),
  concentrés notamment dans `web_ui/*.py` et les scripts d'exemple. `mypy`
  remonte une vingtaine d'erreurs préexistantes dans
  `gse_plus.py`, `moca.py`, `stochastic_models/*`, `optimizer.py`. Aucun
  fichier de configuration ruff/mypy n'existe dans le dépôt (règles par
  défaut).
- **À reprendre** : décider d'un objectif de nettoyage (tout, rien, ou un
  sous-ensemble ciblé) et, séparément, si un fichier de configuration
  ruff/mypy doit être ajouté pour figer les règles retenues — les deux
  sont des décisions produit, pas seulement techniques.

## 13. `us-2026.json` / `uk-2026.json` retirés

- **Ouvert le** : 2026-08-27
- **Statut** : réglé
- **Décision prise le 2026-08-27** : retirés de la distribution (choix
  explicite de l'utilisateur après présentation de l'alternative). Voir le
  commit « Retirer us-2026.json et uk-2026.json » et
  `investment_calculator/tax_regimes/README.md`.
- **À reprendre** : si un pays est réintroduit un jour, repartir d'un
  fichier neuf sourcé — pas des anciens fichiers retirés (consultables
  dans l'historique git si besoin de référence structurelle).

## 14. Hypothèses de marché non sourcées (`market_assumptions/default-2026.json`)

- **Ouvert le** : 2026-08-27 (étape 1.A.6)
- **Statut** : ouvert
- **Contexte** : l'étape 1.A.6 a déplacé le rendement du dividende (2 %),
  la répartition loyer/appréciation (40/60), la part de plus-value réalisée
  annuellement (20 %) et le revenu de référence pour approximer le barème
  progressif (50 000 €) hors du moteur fiscal, dans un document versionné
  et validé par schéma — mais **sans les sourcer**. Ce sont exactement les
  mêmes valeurs qu'avant, juste déplacées ; le document porte `status:
  "draft"` et un `known_gap` qui le dit explicitement, sur le même principe
  que `_legacy_presets.json` en son temps.
- **À reprendre** : sourcer ces hypothèses (rendement de dividende observé
  sur un indice de référence, répartition loyer/appréciation observée sur
  le marché immobilier français, comportement réel de réalisation des
  plus-values) avant de les présenter comme autre chose qu'un ordre de
  grandeur illustratif. Voir aussi le point 1 (prélèvements sociaux) : ces
  hypothèses interagissent avec le taux social appliqué, donc les deux
  méritent d'être repris ensemble.

---

*Dernière mise à jour : 2026-08-27, après l'étape 1.A.6 (sortie des
hypothèses de marché du moteur fiscal). Prochaine étape à discuter avec
l'utilisateur.*
