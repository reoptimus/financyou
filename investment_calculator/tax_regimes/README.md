# Régimes fiscaux

**La fiscalité est une donnée d'entrée du modèle, pas une règle codée dans le moteur.**

Chaque fichier de ce répertoire décrit l'imposition d'un pays pour un millésime.
Ajouter un pays consiste à déposer un fichier JSON. Cela ne demande aucune
modification de code, et ne doit jamais en demander.

**Seule la France (`fr-2026`) est supportée aujourd'hui.** Des régimes `us-2026`
et `uk-2026` ont existé un temps : c'étaient des portages mécaniques des
constantes qui figuraient en dur dans `tax_engine.TaxConfigPreset`, jamais
vérifiés contre une source officielle (leur propre champ `sources` le disait
explicitement : *« AUCUNE »*). Ils ont été retirés à l'étape 1.A plutôt que
complétés : mieux vaut un pays juste qu'un menu de plusieurs drapeaux dont
certains mentent. Un pays s'ajoute en déposant un fichier conforme à
`schema.json`, sourcé, et confronté à des cas d'or — voir « Ajouter un pays »
ci-dessous — pas en réintroduisant une constante non vérifiée.

## Contenu

| Fichier | Rôle |
|---|---|
| `schema.json` | Le contrat. Tout régime doit s'y conformer. |
| `<pays>-<année>.json` | Un régime, par exemple `fr-2026.json`. |
| `_legacy_presets.json` | Valeurs gelées de l'ancien code, conservées le temps de la transition. **À supprimer à la fin de l'étape 1.A.** |

## Statuts

| Statut | Signification | Chargeable en production |
|---|---|---|
| `draft` | Aucune valeur n'a été confrontée à un cas d'or. | Non — `load_regime` lève `DraftRegimeError`. |
| `validated` | Chaque règle est couverte par un cas d'or vérifié, sources citées, validateur humain nommé. | Oui |
| `deprecated` | Millésime remplacé, conservé pour rejouer des simulations archivées. | Oui, avec avertissement |

Aucun régime livré n'est aujourd'hui `validated`. C'est l'objet de l'étape 1.A
de la feuille de route.

## Utilisation

```python
from investment_calculator.tax_regime import list_regimes, load_regime

# Les pays proposés à l'utilisateur se déduisent des fichiers présents.
for descriptor in list_regimes(include_draft=False):
    print(descriptor.country_name, descriptor.fiscal_year)

regime = load_regime("FR", 2026)          # lève DraftRegimeError tant que le régime est un brouillon
regime = load_regime("FR", 2026, allow_draft=True)   # développement uniquement

regime.flat_tax_total_rate()               # 0.30 — et non 0.472
regime.income_tax_due(60_000, shares=2.0)
regime.select_withdrawal_rule("pea", holding_years=6)
regime.eligible_wrappers("equity_eu")      # contrainte transmise à l'optimiseur
```

## Fournir ses propres régimes

Un exploitant peut corriger un millésime ou ajouter un pays sans republier le
paquet, en pointant vers ses propres répertoires :

```bash
export FINANCYOU_TAX_REGIMES=/etc/financyou/regimes:/opt/regimes-clients
```

Ces répertoires sont prioritaires sur ceux embarqués : un fichier `fr-2026.json`
qui s'y trouve masque celui du paquet.

## Ajouter un pays

1. Copier le régime le plus proche, renommer en `<code>-<année>.json`.
2. Renseigner `country`, `fiscal_year`, `currency`, et laisser `status` à `draft`.
3. Décrire les enveloppes de détention du pays : c'est l'unité de modélisation.
   Un actif n'est pas imposé en soi, il est imposé au sein d'une enveloppe.
4. Énumérer honnêtement dans `known_gaps` ce qui n'est pas modélisé. Une lacune
   déclarée est arbitrable ; une lacune silencieuse produit un chiffre faux que
   personne ne remet en question.
5. Lancer `pytest tests/test_tax_regime_contract.py` : le schéma et les
   contrôles sémantiques signalent les incohérences de barème, les enveloppes
   sans cas par défaut, et les doublons.
6. Passer à `validated` seulement après avoir écrit les cas d'or et fait relire
   les valeurs par une personne, nommée dans `validation.validated_by`.

## Ce qui ne va pas ici

Un régime décrit **l'imposition, et rien d'autre**. Les hypothèses de marché et
de comportement — rendement du dividende, part de loyer dans le rendement
immobilier, fraction des plus-values réalisées chaque année — n'ont rien de
fiscal : elles relèvent du générateur de scénarios. Elles se trouvent encore
dans le moteur fiscal et sont explicitement recensées dans le test de garde
`tests/test_tax_regime_contract.py`, en attente de leur déplacement à
l'étape 1.B.

## Conventions

- Les taux s'écrivent en fraction : 17,2 % s'écrit `0.172`, jamais `17.2`.
- L'absence de plafond s'écrit `null`, jamais un infini : `Infinity` n'est pas
  du JSON valide et se propage en `NaN` dans les calculs.
- La dernière tranche d'un barème est ouverte (`"upper": null`).
- Un millésime n'est jamais modifié en place. Une nouvelle année de fiscalité
  donne un nouveau fichier, ce qui garde reproductibles les simulations déjà
  produites.
