# Surfaces de volatilité swaptions

**La surface de volatilité swaptions est une donnée d'entrée du modèle, pas
une formule codée dans le moteur.** Même principe que la courbe des taux
(`investment_calculator/yield_curves/`) et le régime fiscal — voir
`docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md`.

Elle sert à calibrer le paramètre `sigma` (et, sur une bande limitée, `a`)
du modèle Hull-White : voir
`investment_calculator.stochastic_models.calibration.SwaptionCalibrator`.

## Contenu

| Fichier | Rôle |
|---|---|
| `schema.json` | Le contrat. Toute surface doit s'y conformer. |
| `<id>.json` | Une surface, par exemple `eur-synthetic-2026-08.json`. |

## Deux surfaces

| Surface | Nature | Statut |
|---|---|---|
| `eur-bloomberg-2018` | 9 cotations Bloomberg réelles, reprises du calibrage R de 2018 (`legacy/csv_files/Swaptions_V2.csv`) | `draft` : date d'observation et jambe fixe à confirmer par seb |
| `eur-synthetic-2026-08` | grille synthétique, fixture de développement | `draft`, ne peut pas devenir `validated` |

`eur-bloomberg-2018` n'est pas une grille complète : c'est une liste de
cotations (`quotes`), échéances de 3 à 15 ans. Le test
`tests/test_swaption_calibration.py::TestCalibrationContreLeR2018` retrouve,
sur ces cotations et la courbe EIOPA d'avril 2018, le sigma du script R
(`a_sigma.Rda`) à moins de 1 %.

Une surface `validated` doit être réelle (`synthetic: false`), datée
(`observation_date`) et nommer son relecteur (`validation.validated_by`) :
`load_swaption_surface` le vérifie.

### La surface synthétique

`eur-synthetic-2026-08` n'est **pas une cotation de marché** : c'est une
grille produite par un modèle paramétrique lissé, fournie pour débloquer le
portage de `legacy/R_scripts/Calib_Taux_Swaptions_V2.R` en l'absence de
toute donnée de marché dans ce dépôt (voir `known_gaps` du fichier et
`docs/journal-1b-calibration.md`, point 8). Son champ `synthetic` vaut
`true`.

**Interdiction formelle d'en tirer une calibration publiée ou affichée à un
utilisateur.** `load_swaption_surface` et `SwaptionCalibrator.calibrate`
refusent tous les deux de servir/utiliser une surface `synthetic: true` sans
que l'appelant ne passe explicitement `allow_synthetic=True` — le défaut est
`False` précisément pour qu'un usage en production ne puisse pas glisser
silencieusement dessus.

Il n'existe pas de source gratuite fiable pour une vraie surface swaption
EUR (donnée courtier : ICAP/Parameta, LSEG, Bloomberg VCUB, ICE,
Totem...) — voir `HANDOFF_surface_swaptions.md` (dans ce répertoire) pour le
détail de l'approvisionnement envisagé et les décisions encore ouvertes
(valeur de `a` à fixer, horizon de la bande co-terminale, cadence de
rafraîchissement).

## Utilisation

```python
from investment_calculator.swaption_surface import load_swaption_surface

surface = load_swaption_surface("eur-synthetic-2026-08", allow_synthetic=True)
surface.get_vol("3Y", "7Y")  # volatilité normale, bp/an
```

## Ajouter une surface

1. Déposer la donnée source hors dépôt si elle est sous licence (voir
   `known_gaps` : « la surface licenciée reste hors dépôt git »).
2. Créer `<id>.json` conforme à `schema.json` : une grille (`grid`) ou
   une liste de cotations (`quotes`), `currency`,
   `observation_date` (millésime de la surface, pas la date du jour),
   `vol_convention` (`normal` — seule convention supportée à ce jour),
   `fixed_leg_convention`, `synthetic` (`false` pour une vraie source),
   `sources`, `status: "draft"`.
3. Lancer `pytest tests/test_swaption_surface.py` : le schéma et les
   contrôles de cohérence (grille rectangulaire, volatilités positives et
   finies) signalent une erreur de lecture avant qu'un calcul ne s'appuie
   dessus.
4. Ne jamais modifier un fichier de surface existant en place : un nouveau
   millésime donne un nouveau fichier, pour que les simulations archivées
   restent rejouables.
