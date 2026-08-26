# ADR 0001 — Le régime fiscal est une donnée d'entrée du modèle

- **Statut** : accepté
- **Date** : 2026-08-25
- **Étape** : phase 0.4 de la feuille de route de mise en ligne
- **Décideur** : Sébastien Gallet

## Contexte

FinancYou projette un patrimoine après impôt. La fiscalité n'est donc pas un
détail de présentation : elle entre dans le résultat, et elle change les
arbitrages que l'outil recommande.

Dans la version auditée, tout le paramétrage fiscal de cinq pays tenait dans un
dictionnaire Python de 109 lignes, à l'intérieur du moteur
(`tax_engine.TaxConfigPreset`). Cette organisation a produit quatre défauts qui
ne sont pas des accidents mais des conséquences directes du choix de structure :

1. **Un double comptage invisible.** Le régime français portait un taux de 0,30
   pour le prélèvement forfaitaire, auquel le moteur ajoutait ensuite les
   prélèvements sociaux de 0,172 — soit 47,2 % au lieu de 30 %. L'erreur était
   indétectable parce que rien ne distinguait un taux global d'un taux partiel.
2. **Aucune notion de millésime.** Les valeurs dataient de 2018-2020 sans que
   rien ne le dise. Une simulation produite l'an dernier n'était pas rejouable.
3. **Aucune source.** Aucune valeur n'était rattachée à un texte officiel, donc
   aucune n'était vérifiable, donc aucune n'était contestable.
4. **Un coût marginal d'ajout de pays prohibitif.** Ajouter l'Allemagne ou le
   Canada — pourtant annoncés dans l'énumération `TaxJurisdiction` — supposait
   de modifier le moteur. Ils n'ont jamais été ajoutés : `get_preset('DE')`
   levait une exception.

Le produit vise plusieurs pays d'utilisation. Le régime applicable dépend de la
résidence fiscale de l'utilisateur : c'est une caractéristique de l'entrée, au
même titre que son âge ou son horizon de placement.

## Décision

**Le régime fiscal est une donnée d'entrée du modèle, décrite par pays et par
millésime dans des documents JSON validés par un schéma. Le moteur de calcul ne
contient aucun taux, seuil, abattement ou plafond.**

Concrètement :

- Le contrat est `investment_calculator/tax_regimes/schema.json`. Il décrit un
  vocabulaire fiscal général — contributions sociales, barème progressif,
  quotient familial, prélèvement forfaitaire, enveloppes de détention avec
  leurs règles de retrait conditionnelles, abattements pour durée de détention,
  impôt sur la fortune — et non le seul cas français.
- Un régime est un fichier `<pays>-<millésime>.json`. Ajouter un pays est une
  opération de données ; ce n'est jamais une modification de code.
- L'unité de modélisation est l'**enveloppe de détention**, pas la classe
  d'actifs. Un actif n'est pas imposé en soi : il est imposé au sein d'un PEA,
  d'une assurance-vie, d'un ISA ou d'un compte-titres. C'est ce qui permet de
  représenter le PEA, l'antériorité de l'assurance-vie ou le Roth IRA, ce que
  la structure précédente ne pouvait pas faire.
- Chaque régime porte un **statut**. Un régime `draft` est refusé au chargement
  sauf demande explicite : un chiffre que personne n'a validé ne peut pas
  atteindre un utilisateur par inadvertance. Le passage à `validated` exige des
  sources, des cas d'or, et le nom d'une **personne** — un agent peut rédiger un
  régime, il ne peut pas se porter garant de ses valeurs.
- Chaque régime déclare ses **lacunes connues** (`known_gaps`). Une lacune
  déclarée est arbitrable ; une lacune silencieuse produit un chiffre faux que
  personne ne remet en question.
- La liste des pays proposés dans l'interface se déduit des fichiers présents,
  jamais d'une énumération figée.
- Un exploitant peut fournir ses propres régimes via la variable
  d'environnement `FINANCYOU_TAX_REGIMES`, sans republier le paquet.

## Frontière : ce qui n'est pas de la fiscalité

Un régime décrit l'imposition, et rien d'autre. L'audit a montré que le moteur
fiscal contenait aussi des **hypothèses de marché et de comportement** : un
rendement du dividende de 2 %, une répartition 40 % loyer / 60 % appréciation du
rendement immobilier, une fraction de 20 % des plus-values réalisée chaque
année. Ce ne sont pas des paramètres d'imposition, et les loger dans un régime
fiscal reproduirait la confusion qu'on cherche à défaire.

Ces valeurs restent temporairement dans le moteur, explicitement recensées dans
le test de garde, et rejoindront les hypothèses de scénario à l'étape 1.B.

## Mise en application

La décision est rendue exécutoire par des tests, pas par une convention :

- `test_aucun_parametre_fiscal_en_dur_dans_le_moteur` inspecte l'arbre
  syntaxique de `tax_engine.py` et échoue sur tout flottant entre 0 et 1 ou tout
  entier supérieur à 1000 qui ne figure pas dans une liste de tolérances
  annotées. Cette liste ne doit que se réduire.
- `test_la_dette_de_litteraux_ne_grossit_pas` supprime les tolérances devenues
  inutiles, pour qu'elles ne servent pas de budget à consommer.
- `test_aucune_juridiction_en_dur_dans_le_moteur` empêche la réapparition d'un
  dictionnaire indexé par pays.
- `test_le_prelevement_forfaitaire_ne_double_compte_pas_les_contributions_sociales`
  fige le défaut le plus coûteux de l'ancien moteur sous forme de test de
  régression.

## Conséquences

**Favorables.** Les valeurs fiscales deviennent relisibles par une personne qui
n'est pas développeur — un fiscaliste peut relire un JSON commenté, pas un
dictionnaire Python enfoui dans un moteur. Les millésimes rendent les
simulations archivées rejouables. Le coût marginal d'un pays supplémentaire
devient celui de la rédaction d'un fichier. Le double comptage est structurellement
impossible : le schéma sépare la part « impôt sur le revenu » de la part sociale,
et `flat_tax_total_rate()` est la seule manière d'obtenir le taux global.

**Défavorables.** Une dépendance supplémentaire (`jsonschema`). Un niveau
d'indirection entre le calcul et ses paramètres, qui rend le débogage un peu
plus long. Et un risque propre à toute donnée externalisée : un fichier mal
rédigé passe le schéma mais reste faux — c'est pourquoi le statut `validated`
exige des cas d'or, et non seulement une validation syntaxique.

**Transition.** `TaxConfigPreset.get_preset` subsiste, mais ne contient plus de
valeurs : elle lit `tax_regimes/_legacy_presets.json`, extraction fidèle de
l'ancien dictionnaire, et émet un `DeprecationWarning`. Le comportement
numérique est strictement inchangé — les sorties du pipeline sont identiques
octet pour octet. Cette classe et son fichier de données disparaissent à la fin
de l'étape 1.A, quand le moteur consommera directement les régimes.

## Alternatives écartées

**Garder les constantes en Python, en les rangeant mieux.** Rejeté : cela ne
résout ni le millésime, ni la relecture par un non-développeur, ni le coût
d'ajout d'un pays, et laisse le double comptage possible.

**Une base de données.** Rejeté à ce stade : un régime fiscal change une fois par
an et doit être versionné avec le code qui le consomme. Git fait cela mieux
qu'une table, et un fichier se relit en revue de code.

**Un moteur de règles généraliste ou un langage d'expression.** Rejeté :
puissance largement supérieure au besoin, au prix d'un contrat illisible pour un
fiscaliste. Le schéma retenu est délibérément déclaratif et fermé
(`additionalProperties: false`), ce qui permet de détecter une faute de frappe
au chargement plutôt qu'un résultat silencieusement faux.
