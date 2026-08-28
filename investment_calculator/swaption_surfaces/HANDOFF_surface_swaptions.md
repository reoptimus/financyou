# Handoff — Surface de volatilité swaptions comme donnée d'entrée versionnée

> **Destinataire** : discussion Claude Code « régimes fiscaux / données d'entrée ».
> **Origine** : session Cowork du 2026-08-28, projet FinancYou.
> **Rattachement feuille de route** : phase 1.B étape 5 (calibration Hull-White sur
> swaptions), mais le sujet relève du **contrat de données d'entrée** défini en 1.A —
> d'où ce transfert.
>
> **Suite donnée (2026-08-28, même jour) :** voir
> `investment_calculator/swaption_surfaces/eur-synthetic-2026-08.json` (la surface
> versionnée), `investment_calculator/swaption_surface.py` (chargeur, garde-fou
> `synthetic`), `investment_calculator/stochastic_models/calibration.py`
> (`SwaptionCalibrator`, pricing Hull-White par décomposition de Jamshidian) et
> `docs/journal-1b-calibration.md`, point 8. Les trois fichiers CSV et `build_surface.py`
> mentionnés en section 3.3 n'ont pas été transmis avec ce handoff ; seuls le tableau de
> volatilités (section 3.1) et la courbe Nelson-Siegel (section 3.2) ont pu être
> réextraits, depuis le classeur `surface_swaptions_EUR_SYNTHETIQUE.xlsx` fourni
> séparément.

---

## 1. Pourquoi ce sujet arrive dans la discussion « données d'entrée »

Trois objets suivent aujourd'hui le même cycle de vie et doivent suivre les mêmes
règles :

| Donnée | État actuel | Millésime |
|---|---|---|
| Régime fiscal | `fr-2026.json`, chargé, versionné, signé (`validated_by`) | oui |
| Courbe des taux | `EIOPA_avril_2018_FRANCE.xlsx`, à brancher (étape 2) | à faire |
| **Surface swaptions** | **inexistante** — `SwaptionCalibrator` jamais instancié | **à créer** |

`calibrate_hull_white_parameters` (`hull_white.py:450-483`) retourne `a = 0.1` en dur.
Tant qu'aucune surface n'est chargée, ce n'est pas un bug à corriger dans le code : il
manque une donnée d'entrée. Elle doit être traitée exactement comme le régime fiscal —
fichier daté, versionné, référencé dans les métadonnées de chaque simulation, jamais
codée en dur.

---

## 2. Approvisionnement de la vraie donnée

Il n'existe **pas** de source gratuite fiable pour le cube de volatilité swaption EUR.
C'est de la donnée courtier. Par ordre de coût croissant :

1. **Vérifier `legacy/` d'abord.** `Calib_Taux_Swaptions_V2.R` lisait forcément une
   surface quelque part. Si le fichier d'entrée est dans le dépôt, c'est à la fois
   l'entrée de calibration *et* la référence de non-régression — il faut la **même**
   surface pour démontrer l'écart < 1 % exigé par la feuille de route.
2. **ICAP / Parameta Solutions** — la source courtier derrière la plupart des vendeurs,
   vend en direct, généralement moins cher qu'un terminal.
3. **LSEG (Refinitiv)** — chaînes swaption EUR dans Workspace ou via DataScope. Accès
   Datastream universitaire éventuel : les vols ICAP y sont.
4. **Bloomberg VCUB** — le standard, ~25 k€/an/poste.
5. **ICE**, **S&P/Markit Totem** (marques de consensus).
6. Revendeurs (Datarade, FinPricing) : une surface datée ou un historique à quatre
   chiffres plutôt que cinq — suffisant si un cube daté par trimestre suffit.

Repli gratuit acceptable en attendant : les **prix de règlement quotidiens Eurex** sur
options Bund/Bobl/Schatz. Ce sont des options obligataires, pas des swaptions, mais on
en extrait une structure par terme de volatilité de taux EUR défendable et
reproductible. Le portail BCE donne la courbe (jeu YC) mais **aucune** série de vol
swaption.

> **Vérifié le 2026-08-28** (voir `docs/journal-1b-calibration.md`, point 7) :
> `legacy/excel_files/` ne contient aucune donnée de prix de swaption. Le fichier le
> plus proche par le nom, `Extractions Bloomberg - Calibration ESG - ML 1.xlsx`,
> contient des données d'options sur indice actions (SX5E, V2X), pas des swaptions de
> taux. Le point 1 ci-dessus n'a rien donné.

---

## 3. Surface synthétique fournie en attendant

⚠️ **CE NE SONT PAS DES COTATIONS DE MARCHÉ.** Valeurs produites par un modèle
paramétrique lisse, calées à l'œil sur l'ordre de grandeur des vols normales EUR en
régime BCE ~2 %. Usage : fixture de test et portage du script R. **Interdiction
formelle** d'en tirer une calibration publiée ou affichée à un utilisateur.

### 3.1 Volatilité normale ATM, bp/an — swaptions payeuses EUR

| expiry\tenor | 1Y | 2Y | 3Y | 5Y | 7Y | 10Y | 15Y | 20Y | 30Y |
|---|---|---|---|---|---|---|---|---|---|
| 1M | 40.6 | 46.6 | 50.5 | 54.5 | 56.6 | 57.0 | 54.1 | 50.9 | 45.4 |
| 3M | 43.7 | 50.0 | 54.1 | 58.4 | 60.6 | 61.0 | 57.9 | 54.5 | 48.8 |
| 6M | 46.8 | 53.5 | 57.8 | 62.3 | 64.5 | 65.0 | 61.8 | 58.2 | 52.2 |
| 1Y | 51.7 | 58.8 | 63.4 | 68.1 | 70.5 | 71.0 | 67.6 | 63.8 | 57.4 |
| 2Y | 56.4 | 63.6 | 68.3 | 73.1 | 75.5 | 76.0 | 72.6 | 68.8 | 62.3 |
| 3Y | 58.0 | 65.0 | 69.6 | 74.2 | 76.5 | 77.0 | 73.7 | 70.0 | 63.7 |
| 5Y | 57.6 | 64.1 | 68.2 | 72.5 | 74.6 | 75.0 | 72.0 | 68.7 | 62.9 |
| 7Y | 55.9 | 62.0 | 65.8 | 69.7 | 71.6 | 72.0 | 69.3 | 66.2 | 60.8 |
| 10Y | 53.3 | 58.9 | 62.4 | 65.9 | 67.6 | 68.0 | 65.5 | 62.7 | 57.8 |
| 15Y | 48.1 | 53.0 | 56.1 | 59.2 | 60.7 | 61.0 | 58.8 | 56.4 | 52.1 |
| 20Y | 44.2 | 48.7 | 51.5 | 54.3 | 55.7 | 56.0 | 54.0 | 51.8 | 47.9 |

**Convention : volatilité normale (Bachelier), pas lognormale.** C'est la convention du
marché EUR depuis le passage en taux négatifs. Ne jamais alimenter une formule de Black
lognormale avec ces chiffres — c'est le piège classique du portage.

Forme reproduite : bosse en expiry autour de 2-3 ans, montée puis redescente en ténor
avec un maximum vers 7-10 ans, pente en ténor plus raide sur les expiries courtes.

### 3.2 Courbe et forwards associés

Les fichiers embarquent une courbe Nelson-Siegel cohérente
(`b0=3.20 %, b1=-1.35 %, b2=-0.90 %, tau=2.5` — soit ~2.0 % au court, 3.2 % à 30 ans)
et les taux de swap forward ATM ainsi que les annuités qui en découlent. La grille est
donc autoportante et valorisable telle quelle.

> **Point d'attention pour l'étape 2.** Quand la vraie courbe EIOPA sera branchée, il
> faut **recalculer les forwards à partir de cette courbe**. Conserver mes forwards
> donnerait des strikes qui ne sont plus à la monnaie, et une calibration silencieusement
> fausse. Le strike ATM est une fonction de la courbe, pas une donnée de la surface.
>
> **Repris tel quel dans l'implémentation** (voir
> `SwaptionCalibrator._forward_and_annuity`) : les forwards ne sont jamais lus depuis un
> tableau figé, ils sont recalculés à chaque appel à partir de la fonction courbe passée
> au constructeur — Nelson-Siegel de cette surface pour reproduire les vérifications
> ci-dessous, ou une vraie courbe (`investment_calculator.yield_curve`) en production.

### 3.3 Fichiers

| Fichier | Contenu | Reçu ? |
|---|---|---|
| `eur_swaption_atm_volgrid_SYNTHETIC.csv` | grille matricielle expiry × ténor, vols bp | non — reconstruit depuis le classeur Excel |
| `eur_atm_forward_swap_rates_SYNTHETIC.csv` | grille des forwards ATM, % | non |
| `eur_swaption_atm_surface_SYNTHETIC.csv` | format long : vol, forward, annuité, prime | non |
| `build_surface.py` | générateur + pricing HW1F + calibration de vérification | non |

Tous les en-têtes CSV portent la mention `# SYNTHETIC DATA - NOT MARKET QUOTES`. Ne pas
la retirer.

---

## 4. Résultat de vérification — à lire avant d'écrire l'étape 5

La grille a été valorisée sous Hull-White 1F (décomposition de Jamshidian), puis
`a` et `σ` constants ajustés par moindres carrés :

| Jeu d'instruments | a | σ | RMSE | erreur max |
|---|---|---|---|---|
| Cube complet (99 points) | **0.0026** | 61 bp | 8.5 bp | 21 bp |
| Diagonale co-terminale 10 ans (9 points) | 0.0937 | 95 bp | 7.2 bp | — |

**Lecture.** Sur le cube complet la réversion à la moyenne s'effondre vers zéro : c'est
la dégénérescence classique du modèle à un facteur, et elle se produit aussi sur des
données réelles. Conséquences pour l'implémentation :

- **`a = 0.1` en dur n'est pas l'erreur qu'on croyait.** C'est une réversion *fixée*
  raisonnable pour l'EUR. L'erreur est qu'elle n'est ni justifiée, ni documentée, ni
  paramétrable.
- **Schéma de production recommandé** : fixer `a` (0.05-0.10 pour l'EUR, ou l'ajuster
  une fois sur la diagonale), puis calibrer une **σ(t) constante par morceaux** sur une
  **seule bande co-terminale** correspondant à l'horizon de passif visé.
- **Ne pas calibrer sur tout le cube.** On obtiendrait un `a` instable qui saute d'un
  millésime à l'autre, ce qui casse la garantie de reproductibilité de la feuille de
  route.
- Un HW1F à paramètres constants laisse ~7-8 bp d'erreur résiduelle. C'est normal et
  attendu ; le test de non-régression doit tolérer cet ordre de grandeur, pas viser zéro.

> **Vérifié le 2026-08-28** avec une implémentation indépendante (décomposition de
> Jamshidian, `SwaptionCalibrator.calibrate`) : cube complet → a=0.00259, σ=60.7 bp,
> RMSE=8.45 bp, erreur max=21.19 bp (quasi-identique à la ligne ci-dessus). Bande
> co-terminale 10 ans (11 points, sélection par ténor le plus proche par échéance, pas
> nécessairement les 9 mêmes points) → a=0.098, σ=99.7 bp, RMSE=7.48 bp — même ordre de
> grandeur, écart probablement dû à un ensemble de points légèrement différent. Voir
> `tests/test_swaption_calibration.py::TestCalibrationReproduitLesReperesDuHandoff`.

---

## 5. Ce qui est proposé au contrat de données d'entrée

Aligner la surface sur les règles déjà arbitrées pour le régime fiscal :

1. Fichier daté et versionné, hors code, identifiant référencé dans les métadonnées de
   chaque simulation archivée (au même titre que le millésime de courbe et le jeu
   d'hypothèses).
2. Métadonnées obligatoires dans l'en-tête : source, date d'observation, devise,
   convention de volatilité (`normal` / `lognormal`), convention de jambe fixe,
   `validated_by`.
3. Un champ explicite `synthetic: true|false`. Le moteur **refuse** de produire une
   sortie destinée à l'utilisateur à partir d'une surface `synthetic: true` — même
   principe que « une fonctionnalité absente vaut mieux qu'une fonctionnalité qui ment ».
4. La surface licenciée reste hors dépôt git. Seule la fixture synthétique est versionnée,
   pour la suite de tests.

> **Implémenté tel quel** le 2026-08-28 : voir
> `investment_calculator/swaption_surfaces/schema.json` (champs `synthetic`,
> `observation_date`, `currency`, `vol_convention`, `fixed_leg_convention`,
> `validation.validated_by`) et `investment_calculator/swaption_surface.py`
> (`SwaptionSurfaceSyntheticNotAllowedError`, levée par défaut tant que l'appelant ne
> passe pas explicitement `allow_synthetic=True`).

---

## 6. Décisions restant à seb

- Calibration ponctuelle de validation, ou surface rafraîchie en production ? Cela
  tranche entre « acheter un cube daté » et « budgéter un flux ».
- Valeur retenue et justification de `a` fixé.
- Horizon de la bande co-terminale (10 ans ? 20 ans ?) selon l'horizon de projection
  patrimoniale visé.

> Ces trois décisions restent ouvertes : rien dans le code actuel ne fixe `a`, ne choisit
> une bande, ni ne branche `SwaptionCalibrator` sur `market_assumptions` ou
> `ScenarioGenerator`. Voir `docs/journal-1b-calibration.md`, point 8, section
> « décisions ouvertes ».
