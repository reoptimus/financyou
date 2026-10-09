# ADR 0002 — Le placement est l'unité d'optimisation ; GSE++ dépend de l'utilisateur

- **Statut** : accepté
- **Date** : 2026-10-09
- **Étape** : refonte GSE / GSE+ / GSE++, première sous-étape
- **Décideur** : Sébastien Gallet
- **Remplace** : la partie « enveloppes » de l'étape 1.D (PR #25 à #27), pas
  l'ADR 0001, qui reste en vigueur.

## Contexte

FinancYou repose sur une chaîne en trois étages, déjà présente dans le code R
d'origine (`legacy/R_scripts/`) :

1. **GSE** : scénarios des variables financières (taux, actions, immobilier,
   inflation).
2. **GSE+** : les placements accessibles à un foyer (`Produits_placements.R`),
   construits à partir du GSE, avant impôt.
3. **GSE++** : les rendements de ces placements nets de frais et d'impôts
   (`Earn_Aft_Int_TaxesV3.R`), qui dépendent de l'utilisateur (tranche
   marginale, parts) et de la durée de détention.

L'optimisation de Markowitz (`gen_alpha_optim.R`) lit moyenne et volatilité
**sur GSE++**, une allocation par durée de détention.

L'étape 1.D a introduit une autre structure : l'optimiseur choisit des poids
par **actif** sur des rendements avant impôt, un programme linéaire répartit
ensuite ces actifs entre **enveloppes**, et une ponction d'impôt moyenne est
retranchée des rendements par point fixe. La covariance y reste celle d'avant
impôt, l'immobilier en est exclu, et `TaxEngine` (l'ancien GSE+) rembourse une
partie des pertes des années négatives. L'analyse est dans
`analyses/gse-apres-impot-markowitz-2026-10-08.md` (dossier du projet).

## Décision

1. **L'unité d'optimisation est le placement**, par exemple « actions en PEA »
   ou « assurance-vie, fonds en euros ». Un placement associe un support (une
   ou plusieurs séries du GSE, ou un modèle de produit) à une enveloppe du
   régime fiscal.
2. **L'enveloppe reste la règle fiscale** du placement, lue dans
   `tax_regimes/*.json` (ADR 0001). Elle cesse d'être une dimension
   d'optimisation : plus de programme linéaire de placement, plus de point
   fixe, plus de ponction moyenne.
3. **Les placements sont une donnée d'entrée**, décrite par pays et millésime
   dans `investment_calculator/placement_catalogs/*.json`, validée par
   `placement_catalogs/schema.json`. Frais, composition des supports et
   paramètres des modèles de produit y figurent avec leurs sources ; aucun
   n'est écrit dans le code. Comme un régime, un catalogue `draft` est refusé
   au chargement et `validated_by` nomme une personne.
4. **GSE++ est calculé par utilisateur** : rendement net par scénario, durée
   de détention H et placement.
5. **Moyenne et covariance sont lues sur GSE++, à l'horizon H**, sans
   correction après coup. Seuls les plafonds de versement des enveloppes
   restent des contraintes de l'optimiseur.

## Conséquences

- `modules/tax_engine.py` est remplacé par un module GSE+ (séries brutes par
  placement) et un module GSE++ (rendements nets).
- `wrapper_tax.py` est conservé et étendu à toutes les durées de détention.
- `wrapper_allocation.py` ne garde que les plafonds.
- Les chiffres du pipeline d'exemple changent ; chaque sous-étape le mesure.
- Le Pinel n'est pas repris : aucun nouvel investissement n'y est possible
  depuis le 1er janvier 2025 ([service-public.gouv.fr, F31151](https://www.service-public.gouv.fr/particuliers/vosdroits/F31151)).
