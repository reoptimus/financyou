# Validation 1.A — Cas d'or du régime fiscal `fr-2026`

- **Étape** : 1.A (banc de cas d'or, remplissage des lacunes, valeurs proposées)
- **Rédigé par** : un agent (Claude), sur la branche `phase-1a-fiscalite`
- **Date** : 2026-08-27
- **Statut du régime** : reste `draft`. Aucun champ `validated_by` n'a été renseigné et ne doit
  pas l'être à partir de ce rapport — voir
  [ADR 0001](../adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md) : un agent peut rédiger un
  régime, il ne peut pas se porter garant de ses valeurs. Ce document sert à **informer une
  décision humaine**, pas à s'y substituer.

Ce rapport couvre les étapes 1.A.1 à 1.A.3 (trois commits sur `phase-1a-fiscalite`) et s'arrête
avant l'étape 1.A.5 (branchement du moteur), conformément à la consigne reçue.

## À lire en premier : une incertitude majeure a été découverte en cours de route

En vérifiant les taux **déjà présents** dans `fr-2026.json` (PFU, PEA, PER — hors des cinq
lacunes qui m'avaient été assignées), la recherche a fait remonter, avec un fort niveau de
corroboration (une dizaine de sources indépendantes : cabinets d'avocats, banques privées,
presse patrimoniale, et la brochure officielle impots.gouv.fr « Principales nouveautés Revenus
2025 ») :

> La loi de financement de la sécurité sociale pour 2026 (adoptée définitivement le 16/12/2025)
> porte la CSG sur certains revenus du capital de 9,2 % à 10,6 %, soit des **prélèvements sociaux
> de 18,6 % au lieu de 17,2 %**, avec effet **dès les plus-values et revenus 2025** (déclaration
> 2026), pour : plus-values mobilières, dividendes, compte-titres, PEA, PER, épargne salariale,
> LMNP, crypto-actifs. Restent à 17,2 % : assurance-vie, épargne réglementée (Livret A...),
> immobilier non meublé (revenus fonciers et plus-values immobilières).

`fr-2026.json` applique aujourd'hui un taux unique de 17,2 % à tout
(`social_contributions.investment_income.rate` et `flat_tax.social_rate`), **ce qui sous-estime
l'impôt dû sur les enveloppes CTO, PEA et PER pour les revenus 2025**. Je n'ai pas corrigé ce
point dans cette itération : le corriger correctement suppose de faire porter le taux social par
enveloppe (ou par catégorie de revenu), avec la bonne date d'effet, ce qui est un changement de
modélisation plus large que les cinq lacunes qui m'avaient été confiées et mérite sa propre étape
plutôt qu'un ajustement rapide. J'ai :

- retiré les valeurs attendues de `cto_pfu_plus_value`, `pea_retrait_apres_cinq_ans`,
  `pea_retrait_avant_cinq_ans` et `per_sortie_capital_retraite` (elles utilisaient 17,2 % ; je ne
  voulais pas laisser un chiffre probablement faux au statut `ready`) ;
  ces quatre cas repassent à `pending_regime_data` ;
- ajouté un `known_gap` dédié, des deux côtés (`fr-2026.json` et `tests/golden/fr-2026.json`,
  cas `prelevements_sociaux_18_6_pourcent_2025`).

Source principale : [impots.gouv.fr — Principales nouveautés Revenus 2025](https://www.impots.gouv.fr/www2/fichiers/documentation/brochure/ir_2026/pdf_som/nouveautes.pdf),
p. 45, consultée le 2026-08-27. Recoupée par des sources professionnelles concordantes (Banque
Transatlantique, DLA Piper, CIC, Mon Petit Placement, entre autres) — voir le detail dans les
`notes` des cas concernés.

**Recommandation** : traiter ceci comme un point bloquant avant de considérer le régime prêt à
être validé, même pour les enveloppes qui ne font pas partie des cinq lacunes d'origine.

## Tableau des cas

### Cas prêts (`status: ready`), avec source et confiance

| Cas | Description courte | Valeur proposée (total) | Confiance | Source principale |
|---|---|---|---|---|
| `ir_bareme_celibataire_tranche_30` | IR, célibataire, 40 000 €, 1 part | 5 103,99 € | Élevée | service-public.fr A18045 |
| `ir_bareme_couple_deux_enfants` | IR, couple 2 enfants, 80 000 €, 3 parts, sans plafonnement | 4 972,00 € | Élevée | service-public.fr A18045 |
| `ifi_patrimoine_deux_millions` | IFI, patrimoine 2 M€ | 7 400,00 € | Élevée | Légifrance art. 977 CGI, BOFiP BOI-PAT-IFI-40-10 |
| `assurance_vie_rachat_primes_sous_seuil` | AV > 8 ans, primes 100 k€, abattement absorbe tout | 595,38 € | Élevée | Légifrance art. 125-0 A |
| `assurance_vie_rachat_primes_au_dela_du_seuil` | AV > 8 ans, primes 200 k€ | 5 932,94 € | **Moyenne** | Légifrance art. 125-0 A |
| `assurance_vie_rachat_avant_huit_ans` | AV < 8 ans | 1 038,46 € | Élevée | Légifrance art. 125-0 A |
| `livret_a_retrait_exonere` | Livret A, exonération totale | 0,00 € | Élevée | CMF art. L221-5 |
| `immobilier_direct_cession_apres_abattements` | Plus-value immobilière nette de 30 000 € | 10 860,00 € | Élevée | impots.gouv.fr |
| `ir_plafonnement_quotient_familial_general` | Plafonnement général du quotient, revenu 300 000 € | 86 987,04 € | **Moyenne** | BOFiP BOI-IR-LIQ-20-20-20 |
| `cehr_celibataire_hauts_revenus` | CEHR, célibataire, RFR 600 000 € | 258 023,84 € | Élevée | Légifrance art. 223 sexies CGI |
| `cehr_couple_hauts_revenus` | CEHR, couple, RFR 600 000 € | 226 047,68 € | Élevée | Légifrance art. 223 sexies CGI |

Le détail du calcul (tranche par tranche, avec les montants intermédiaires) figure dans le champ
`notes` de chaque cas, dans `tests/golden/fr-2026.json`, pour permettre une relecture sans exécuter
de code.

**Deux cas à confiance « moyenne », à relire en priorité :**

- `assurance_vie_rachat_primes_au_dela_du_seuil` — la valeur appliquée simplifie la règle réelle :
  le régime applique le taux de 12,8 % à la totalité de la quote-part de gain retirée, alors que
  la règle du BOFiP (BOI-RPPM-RCM-20-15) ne l'applique qu'à la fraction du gain rattachée aux
  primes dépassant 150 000 €, calculée proportionnellement à l'encours net de rachats. C'est
  exactement la lacune déclarée `assurance_vie_encours_primes_net_de_rachats`. La valeur proposée
  est donc celle que produit la simplification actuelle, pas le montant réellement dû par un
  contribuable dans cette situation.
- `ir_plafonnement_quotient_familial_general` — le montant du plafond lui-même (1 807 € par
  demi-part) n'a été confirmé que par des sources secondaires concordantes (BOFiP lu via une
  extraction automatisée, LégiFiscal), pas par une relecture humaine directe du texte BOFiP brut.

### Cas retirés en cours de route (incertitude majeure ci-dessus)

| Cas | Raison |
|---|---|
| `cto_pfu_plus_value` | Utilise le taux social 17,2 %, probablement 18,6 % pour une cession 2025 |
| `pea_retrait_apres_cinq_ans` | Idem |
| `pea_retrait_avant_cinq_ans` | Idem |
| `per_sortie_capital_retraite` | Idem, cumulé à la simplification déjà connue sur `resolve_income_tax_rate` |

### Cas `known_gap` (échec structurel documenté, pas une question de valeur)

| Cas | Nature de la lacune |
|---|---|
| `quotient_familial_plafonnement_cas_particuliers` | Cas particuliers du plafonnement (parent isolé, veuf, garde alternée, invalides) non modélisés |
| `cdhr_hauts_revenus` | Existence et paramètres de la CDHR pour 2025 non confirmés auprès d'une source primaire |
| `per_plafond_deduction` | Formule proposée dans le schéma, mais le calcul dépend d'une donnée personnelle (revenu N-1) hors périmètre d'un régime |
| `assurance_vie_encours_primes_net_de_rachats` | Nécessite un suivi dans le temps, hors de portée d'un régime sans état |
| `revenus_fonciers_micro_et_reel` | Catégorie de revenu récurrent non intégrée au moteur |
| `prelevements_sociaux_18_6_pourcent_2025` | Voir section précédente |
| `ifi_decote_entree_1_3_a_1_4_million` | Décote d'entrée (1,3-1,4 M€) non implémentée par `wealth_tax_due` ; sans effet sur `ifi_patrimoine_deux_millions` |
| `surtaxe_plus_value_immobiliere_seuil_a_verifier` | Dernier seuil probablement 260 000 € et non 250 000 € ; champ non consommé par le moteur à ce stade |

## Incertitudes déclarées explicitement (résumé)

Conformément à la consigne « cinq incertitudes déclarées valent mieux qu'une erreur silencieuse »,
voici la liste complète des points sur lesquels je ne suis pas sûr à 100 %, du plus au moins
important :

1. **Taux social 18,6 % vs 17,2 % pour les revenus 2025** (voir plus haut) — impact potentiel sur
   toutes les enveloppes concernées, pas seulement les quatre cas retirés.
2. **Formule PER pour les travailleurs non-salariés** (`contribution_deduction_formula.tns_*`) —
   la recherche a obtenu des extractions BOFiP contradictoires sur l'année de référence du PASS et
   le signe du terme à 15 %. Confiance faible, signalée dans `known_gaps`.
3. **Statut de la CDHR pour les revenus 2025** — un agent de recherche a rapporté une
   « pérennisation conditionnelle » avec un numéro de loi précis, mais a lui-même signalé ne pas
   avoir pu lire le texte source brut (accès bloqué, résumé seulement). Je n'ai pas retenu cette
   affirmation dans le régime : elle reste un `known_gap`, pas une valeur.
4. **Plafond du quotient familial (1 807 €)** et **quart de part (904 €)** — confirmés par des
   sources secondaires concordantes, pas par une lecture directe du BOFiP brut.
5. **Seuil du dernier palier de la surtaxe sur les plus-values immobilières** — probablement
   260 000 € et non 250 000 €, mécanisme de décote non reproduit par de simples tranches
   marginales ; sans effet aujourd'hui car le champ n'est consommé par aucun calcul.
6. **Décote d'entrée de l'IFI (1,3-1,4 M€)** — non implémentée ; sans effet sur le cas d'or fourni
   (2 M€, largement au-dessus).

## Hors périmètre de cette étape, non traité

- `us-2026.json` et `uk-2026.json` : non touchés. Le prompt de départ demandait d'envisager leur
  retrait pur et simple si je jugeais qu'ils ne sont que des constantes non vérifiées ; je ne l'ai
  pas fait, faute de temps dans cette itération, et je ne veux pas trancher seul une décision qui
  affecte la distribution du produit. **Recommandation** : traiter cette question dans une étape
  dédiée plutôt que d'y répondre en marge de la fiscalité française.
- PEA-PME, PEA jeunes, prélèvement forfaitaire non libératoire (acompte) : `known_gaps`
  pré-existants, non traités car hors des cinq points assignés à l'étape 1.A.2.
- Barème de l'IFI pour 2026 : confirmé correct par la recherche (inchangé depuis 2018), mais le
  `known_gap` « à vérifier » n'a pas été retiré du fichier faute de relecture humaine formelle du
  texte — je préfère laisser la mention plutôt que m'auto-certifier.

## Vérifications d'environnement (contraintes permanentes)

- `pytest tests/` : 289 passed, 1 skipped, 12 failed (tous les échecs sont les cas documentés
  ci-dessus). Aucune régression sur les 278 tests pré-existants.
- `ruff check` et `mypy` : verts sur tous les fichiers Python modifiés par les trois commits de
  cette étape (`investment_calculator/tax_regime.py`, `tests/golden/loader.py`,
  `tests/test_golden_fr_2026.py`, `tests/test_tax_regime_contract.py`). Le dépôt porte par
  ailleurs une dette de lint et de typage préexistante, non liée à la fiscalité (environ 540
  diagnostics ruff et une quinzaine d'erreurs mypy dans `gse_plus.py`, `moca.py`,
  `stochastic_models/`, `optimizer.py`) : je ne l'ai pas résorbée, elle est hors périmètre.
- `python examples/complete_pipeline_with_files.py` : échoue, **mais échoue à l'identique sur la
  branche `phase-0.4`** (avant tout travail de cette étape) — vérifié en restaurant temporairement
  les fichiers de `phase-0.4` puis en revenant à `phase-1a-fiscalite` (aucune perte de travail :
  les trois commits étaient déjà enregistrés). La cause est un répertoire `outputs/` absent
  (ignoré par git, jamais créé par un script d'installation) et, sur cet environnement Windows,
  un encodage de console qui n'accepte pas certains caractères Unicode (✓/✗) tant que
  `PYTHONIOENCODING=utf-8` n'est pas positionné. Ce n'est pas une régression introduite par cette
  étape : le moteur fiscal n'est pas encore branché sur les nouveaux régimes (étape 1.A.5), donc
  rien de ce qui a changé ici n'affecte ce script.

## Ce que ce rapport ne fait pas

Il ne déclare aucune valeur `validated`, ne renseigne aucun `validated_by`, et ne recommande pas
de le faire à partir de mon seul travail. Il documente ce qui a été fait, avec quelle confiance, et
ce qui doit encore être tranché par une personne avant de considérer `fr-2026.json` autre chose
qu'un brouillon avancé.

## Prochaines étapes proposées (attendent la validation humaine)

1. Décider comment traiter l'incertitude majeure (taux social 18,6 %) : corriger maintenant dans
   une étape dédiée, ou accepter le `known_gap` et avancer avec les enveloppes non concernées.
2. Faire relire par un fiscaliste au moins les points à confiance « moyenne » ou « faible »
   listés ci-dessus.
3. Si le régime est jugé prêt pour les usages qu'il couvre déjà : renseigner `validated_by`,
   `validated_on` et `golden_cases` dans `fr-2026.json`, en gardant les `known_gaps` restants
   (le statut `validated` n'exige pas l'absence de lacune, seulement qu'elle soit déclarée).
4. Une fois ces décisions prises : passer à l'étape 1.A.5 (brancher le moteur), sur autorisation
   explicite — pas avant.
