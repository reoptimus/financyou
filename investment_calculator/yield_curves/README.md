# Courbes des taux

**La courbe des taux sans risque est une donnée d'entrée du modèle, pas une
formule codée dans le moteur.** Voir
`docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md` : même principe,
appliqué à un autre type de donnée de marché.

## Contenu

| Fichier | Rôle |
|---|---|
| `schema.json` | Le contrat. Toute courbe doit s'y conformer. |
| `<id>.json` | Une courbe, par exemple `eiopa-fr-2018-04.json`. |

Un fichier de courbe ne contient **pas** les taux eux-mêmes : il référence
un fichier source (typiquement dans `legacy/`, en lecture seule — voir
`CLAUDE.md`) et les paramètres de lecture (feuille, colonne, lignes). Le
calcul (bootstrap, interpolation, lissage) est délégué à
`investment_calculator.stochastic_models.calibration.EIOPACalibrator`.

## Aujourd'hui : une seule courbe, un seul pays

`eiopa-fr-2018-04` est la seule courbe livrée : un portage du fichier EIOPA
France d'avril 2018 qui traînait dans `legacy/`, jamais réellement chargé
avant l'étape 1.B.2 (`EIOPACalibrator.from_excel` n'avait aucun appelant, et
ses paramètres par défaut ne correspondaient même pas à la structure réelle
du classeur). Son statut reste `draft` : le chargement a été vérifié
cohérent (voir `known_gaps` du fichier), mais personne n'a relu les valeurs
elles-mêmes contre la publication EIOPA d'origine.

C'est un millésime de 2018 : il ne reflète pas les conditions de marché
actuelles. C'est la seule courbe disponible aujourd'hui, pas une
recommandation d'usage en production.

## Utilisation

```python
from investment_calculator.yield_curve import list_yield_curves, load_yield_curve

for c in list_yield_curves():
    print(c["id"], c["vintage_date"], c["status"])

curve = load_yield_curve("eiopa-fr-2018-04")
curve.get_forward_curve(n_steps=60)
curve.get_bond_prices(n_steps=60)
```

`ScenarioGenerator._generate_stochastic` accepte un `yield_curve_id` dans sa
configuration ; à défaut, la courbe par défaut ci-dessus est utilisée pour
l'EUR. L'identifiant et le millésime de la courbe utilisée sont consignés
dans `metadata.calibration_info` de chaque simulation — une simulation
archivée doit pouvoir être rejouée à l'identique en s'y référant.

## Ajouter une courbe

1. Déposer le fichier source (Excel/CSV) quelque part de versionné — dans
   `legacy/` seulement s'il s'agit réellement d'une référence héritée ;
   sinon dans un répertoire dédié aux données de marché courantes.
2. Créer `<id>.json` conforme à `schema.json` : `country`, `currency`,
   `vintage_date` (la date de publication de la courbe, pas la date du
   jour), `source` (chemin, feuille, colonne, lignes), `status: "draft"`.
3. Lancer `pytest tests/test_yield_curve.py` : le schéma et les contrôles
   de cohérence (`P(0,t)` dans des bornes plausibles, décroissant aux
   longues maturités) signalent une mauvaise colonne ou un décalage de
   ligne avant qu'un calcul ne s'appuie dessus.
4. Ne jamais modifier un fichier de courbe existant en place : un nouveau
   millésime donne un nouveau fichier, pour que les simulations archivées
   restent rejouables.
