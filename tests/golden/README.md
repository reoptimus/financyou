# Banc de cas d'or — France, millésime 2026

Ce répertoire contient les **cas d'or** : des situations fiscales concrètes,
avec le résultat qu'elles doivent produire au centime près. Ils servent à
vérifier que le régime fiscal `investment_calculator/tax_regimes/fr-2026.json`
calcule le bon montant — pas seulement qu'il respecte un schéma.

Voir `docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md` pour le
principe général : la fiscalité est une donnée d'entrée, pas du code.

## Qui doit pouvoir lire ce fichier

`fr-2026.json` dans ce répertoire est écrit pour être relu par un fiscaliste
ou un product owner qui ne lit pas Python. Chaque cas est un objet JSON avec
des champs en clair (pas d'abréviation) et une `description` en français.
Aucune valeur attendue ne doit être ajoutée sans une source à l'appui — voir
le champ `sources` de chaque cas.

## Structure d'un cas

```jsonc
{
  "id": "identifiant-stable-en-minuscules",
  "description": "Une phrase qui décrit la situation en langage courant.",
  "kind": "wrapper_withdrawal",   // voir « Les quatre familles » ci-dessous
  "status": "pending_expected_value", // voir « États d'un cas » ci-dessous
  "inputs": { /* dépend de kind, voir ci-dessous */ },
  "expected": {
    "income_tax": null,             // impôt sur le revenu dû, en euros, ou null si pas encore établi
    "social_contributions": null,   // prélèvements sociaux dus, en euros, ou null
    "total": null,                  // income_tax + social_contributions
    "net": null                     // ce que le foyer reçoit réellement après impôt
  },
  "sources": [
    { "label": "...", "url": "...", "consulted_on": "AAAA-MM-JJ" }
  ],
  "confidence": "high | medium | low",  // absent tant que le cas n'est pas rempli
  "notes": "Toute réserve, hypothèse ou incertitude à signaler."
}
```

Un montant dans `expected` est en euros, avec deux décimales si nécessaire —
c'est la précision « au centime » exigée par le test. `null` signifie
« non établi », jamais « zéro » : ne mettez `0` que si le résultat correct
est vraiment zéro.

## Les quatre familles de cas (`kind`)

- **`income_tax`** — impôt sur le revenu d'un foyer sur un revenu imposable
  donné, hors tout retrait d'enveloppe. `inputs` : `taxable_income`, `shares`.
- **`wealth_tax`** — impôt sur la fortune immobilière sur un patrimoine net
  taxable donné. `inputs` : `net_taxable_wealth`.
- **`wrapper_withdrawal`** — retrait d'une enveloppe de détention (PEA,
  assurance-vie, PER, CTO, Livret A, immobilier direct). `inputs` :
  `wrapper_id`, `withdrawal_amount`, `gain_amount`, `holding_years`, `age`,
  `premiums_paid`, `account_value`, `exit_form`, `shares`.
  Tous les champs de `inputs` ne sont pas requis pour chaque enveloppe :
  seuls ceux que la règle de retrait de l'enveloppe évalue comptent (voir
  `withdrawal_rules[].when` dans le régime).
- **`known_gap`** — un cas volontairement non calculable aujourd'hui parce
  que le régime porte une lacune connue (voir `known_gaps` dans
  `fr-2026.json`). `inputs` et `expected` sont absents ; `blocked_reason`
  explique quelle lacune bloque le calcul. Ce cas échoue tant que la lacune
  n'est pas comblée — c'est voulu : il sert de rappel exécutable.

## États d'un cas (`status`)

- `pending_regime_data` — le régime ne porte pas encore (ou pas correctement)
  la règle nécessaire à ce calcul.
- `pending_expected_value` — le régime porte la règle, mais la valeur
  attendue n'a pas encore été établie ou sourcée.
- `pending_schema_extension` — le schéma des régimes ne permet pas d'exprimer
  cette règle ; une extension est proposée ailleurs (voir le rapport de
  validation).
- `ready` — `expected` est rempli, sourcé, et le cas doit passer.

## Pourquoi tout échoue au départ

À la création de ce banc, `fr-2026.json` (le régime) est encore un
brouillon et aucune valeur attendue n'a été établie : tous les cas ont donc
`status` différent de `ready` et échouent. C'est le comportement voulu — voir
`tests/test_golden_fr_2026.py`.
