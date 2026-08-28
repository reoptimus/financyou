# Journal — étape 1.B, calibration et cohérence de marché

Même principe que `docs/journal-fiscalite.md` (étape 1.A), pour un chantier
différent : ce document recense les questions en suspens, les décisions déjà
prises, et les points à reprendre plus tard, au fil de l'étape 1.B.

---

## 1. RealEstateModel : le processus auxiliaire explose (bug majeur, distinct du bug actions)

- **Ouvert le** : 2026-08-27 (étape 1.B.1, en étendant le test de martingalité)
- **Statut** : ouvert — hors périmètre de l'étape 1.B.3 telle que cadrée
- **Contexte** : en étendant le test de martingalité à l'immobilier,
  `D(t)*Index_immo(t)` diverge de plusieurs ordres de grandeur (jusqu'à 1e18
  sur un tirage à 10 000 scénarios, 30 ans, pas de 0,25 an), alors que
  l'équivalent actions ne s'écarte « que » d'environ 18 %.
- **Cause identifiée** : `RealEstateModel._generate_auxiliary_rates`
  (`stochastic_models/real_estate.py`) utilise la volatilité **immobilière**
  (`sigma`, typiquement 12 %) pour diffuser un processus auxiliaire `r2(t)`
  censé se comporter comme un taux court à la Hull-White — dont la
  volatilité réaliste est de l'ordre de 1 %. Le processus auxiliaire prend
  des valeurs observées jusqu'à ±108 % sur 30 ans (`auxiliary_rates.max()`
  ≈ 1.08, `.min()` ≈ -1.05 dans le test empirique). Le retour de prix
  immobilier dépend de `(r2(t) - k(t)) * K(dt)` : un `r2` de cette
  amplitude produit un rendement de période aberrant, et la somme cumulée
  de plusieurs tels rendements, une fois exponentiée, explose.
- **Pourquoi ce n'est pas la même chose que le bug actions** : le bug
  actions (`black_scholes.py`, drift `r+σ²/2`) est une erreur de SIGNE sur
  un terme de correction — le modèle reste stable, juste mal centré. Le
  bug immobilier est une **instabilité numérique du modèle lui-même** : il
  ne suffira pas de changer un signe de drift pour le corriger, il faut
  revoir la calibration du processus auxiliaire (a minima, ne pas réutiliser
  la volatilité immobilière comme volatilité de taux).
- **Ce qui a été fait pour l'étape 1.B.1** : le test de martingalité couvre
  désormais ce cas (`tests/test_scenario_generator.py::test_martingale_immobilier_est_risque_neutre`),
  marqué `xfail` avec une raison explicite pointant ici. La CI reste verte ;
  la lacune est visible (`xfailed`, pas masquée) plutôt que silencieuse.
- **À reprendre** : revoir `_generate_auxiliary_rates` — probablement
  séparer clairement un paramètre de volatilité propre au processus
  auxiliaire (petit, de l'ordre de celui du taux court) de la volatilité de
  prix immobilier réellement observée (qui, elle, doit gouverner la
  diffusion du PRIX, pas d'un taux intermédiaire). Ce point doit
  probablement être traité AVANT l'étape 1.B.3 pour l'immobilier
  spécifiquement : séparer risque-neutre et monde réel n'a pas de sens tant
  que le socle risque-neutre lui-même explose.

## 2. Indexation des colonnes de `deflators_df` (t_1..t_N) vs convention interne (colonne i = D(i·dt))

- **Ouvert le** : 2026-08-27 (étape 1.B.1)
- **Statut** : ouvert, mineur
- **Contexte** : en corrigeant `_test_martingale`, il a fallu établir que
  `deflators[:, i]` (et de même pour les rendements actions/immobilier)
  représente la valeur au temps `i*dt`, avec `deflators[:, 0] == 1`
  trivialement (D(0)=1). Mais `_generate_stochastic` nomme les colonnes du
  DataFrame exposé `deflators_df` par `t_{i+1}` (1-indexé), ce qui laisse
  penser que la colonne `i` correspond au temps `(i+1)*dt`, pas `i*dt`.
  Le libellé n'est pas nécessairement faux si on le lit comme « période
  ordinale n° i+1 » plutôt que comme une valeur de temps littérale, mais
  c'est ambigu et mérite clarification.
- **À reprendre** : soit renommer les colonnes pour porter la valeur de
  temps réelle (`t_{i*dt}`), soit documenter explicitement la convention
  ordinale dans la docstring de sortie. Ne pas casser silencieusement un
  consommateur existant de ces noms de colonnes sans vérifier.

## 3. `Rt[:, 0]` et équivalents restent à 0 par construction (pas un bug, mais à documenter)

- **Ouvert le** : 2026-08-27 (étape 1.B.1)
- **Statut** : réglé — compris et exploité, pas un bug
- **Contexte** : `HullWhiteModel.generate_scenarios` initialise `Rt` à
  `np.zeros(...)` et ne peuple qu'à partir de l'indice 1 dans la boucle
  (`for i in range(n_steps-1): Rt[:, i+1] = ...`). Il en va de même pour
  `BlackScholesEquity._calculate_total_returns`. C'est ce qui garantit que
  `deflators[:, 0] == 1` et `equity_index[:, 0] == 1`, cohérent avec
  `D(0)=1` et `Index(0)=1` — la convention exploitée par le test de
  martingalité corrigé.
- **Point de vigilance** : `RealEstateModel._generate_price_returns`, lui,
  peuple `price_returns[:, 0]` dès le premier passage de boucle (pas de
  saut à l'indice 1) — donc `real_estate_index[:, 0] != 1` en général, à la
  différence des deux autres modèles. Ce n'est pas la cause principale de
  l'explosion (point 1 ci-dessus est bien plus sévère), mais c'est une
  incohérence de convention entre les trois modèles qui mériterait d'être
  alignée en même temps que la correction du point 1.

## 4. Bug composé dans le drift risque-neutre actions (`black_scholes.py`), corrigé à l'étape 1.B.3

- **Ouvert et réglé le** : 2026-08-28 (étape 1.B.3, en implémentant la
  séparation risque-neutre / monde réel)
- **Statut** : réglé
- **Contexte** : `_calculate_total_returns` était déjà repéré comme
  « mal centré » au point 3 ci-dessus (`+σ²/2` au lieu de `-σ²/2`), avec un
  écart résiduel d'environ 18 % à 30 ans jugé peu sévère par rapport au bug
  immobilier. En corrigeant uniquement ce signe pour préparer la prime de
  risque, l'écart n'a pas disparu : il a bougé (`E[D(t)*Index(t)]` ≈ 1,18 au
  lieu de ≈ 0,82), ce qui a révélé un second bug, distinct et cumulatif :
  `short_rates[:, t]` (le `Rt` produit par `HullWhiteModel`) est déjà un
  rendement de PÉRIODE — exactement ce que `_calculate_deflators` accumule
  sans le multiplier par `dt`. L'ancien code le multipliait pourtant une
  seconde fois par `dt` dans le drift actions, comme s'il s'agissait d'un
  taux annualisé, ce qui le sous-comptait par rapport à ce que le déflateur
  retire réellement à chaque période.
- **Correction** : `drift = short_rates[:, t] + (risk_premium - σ²/2) * dt`
  — seuls `risk_premium` et la correction d'Itô (des taux annualisés) sont
  mis à l'échelle par `dt` ; `short_rates[:, t]` ne l'est plus. Vérifié
  empiriquement (`n_scenarios=20000`, `dt=0,25`, courbe EIOPA France,
  graine 42) : `E[D(t)*Index(t)]` passe à 1,00026 à 30 ans, contre ≈ 1,18
  avec le seul signe corrigé et une divergence plus grande encore avec le
  code d'origine. Voir `tests/test_stochastic_models.py::TestBlackScholesEquity`
  pour les deux tests déterministes qui isolent chaque terme du drift, et
  `tests/test_scenario_generator.py::test_martingale_equity_est_risque_neutre`
  (désormais un test qui passe, plus un `xfail`) pour la vérification Monte
  Carlo bout en bout.
- **Conséquence sur les nombres déjà produits** : toute simulation générée
  avant cette correction avait un indice actions risque-neutre biaisé, et
  — une fois la prime de risque introduite à la même étape — un indice
  actions monde réel qui héritait du même biais de drift. `scenarios_df`
  change donc de valeurs à partir de cette étape ; voir la comparaison
  avant/après dans la description de la PR (`examples/complete_pipeline_with_files.py`,
  règle « Aucune régression numérique silencieuse » de `CLAUDE.md`).

## 5. Prime de risque immobilière : rattachée à un modèle risque-neutre déjà instable (point 1)

- **Ouvert le** : 2026-08-28 (étape 1.B.3)
- **Statut** : ouvert — documenté, pas corrigé, hors périmètre de 1.B.3
- **Contexte** : par cohérence d'interface avec les actions,
  `RealEstateModel.generate_returns` accepte désormais un paramètre
  `risk_premium`, appliqué à un drift déjà annualisé (`kimmo`), et
  `ScenarioGenerator` l'alimente avec `assumptions.real_estate_risk_premium`
  (1,5 %, voir `docs/validation/1b-hypotheses-monde-reel.md`). Cela **ne
  corrige pas** l'explosion documentée au point 1 : le socle risque-neutre
  immobilier reste instable à 30 ans, la prime de risque s'ajoute
  simplement à un drift qui explose déjà pour une autre raison.
  L'illustration à 30 ans de `docs/validation/1b-hypotheses-monde-reel.md`
  contourne le problème en calculant l'effet de la prime analytiquement
  (capitalisation à taux constant), plutôt qu'en faisant tourner
  `RealEstateModel`.
- **À reprendre** : corriger le point 1 avant de considérer qu'une
  projection immobilière monde réel produite par `RealEstateModel` est
  utilisable pour un utilisateur.

## 6. Constantes économiques extraites en donnée versionnée (étape 1.B.4)

- **Ouvert et réglé le** : 2026-08-28 (étape 1.B.4)
- **Statut** : réglé, avec deux lacunes ouvertes documentées ci-dessous
- **Contexte** : `ScenarioGenerator.__init__` et `GlobalScenarioEngine.__init__`
  (`scenario_generator.py`, `gse.py`) avaient chacun leur propre copie en
  dur des mêmes constantes ("US historical averages" : volatilité actions
  18 %, dérive immobilière 8 %, inflation 2,5 %, matrice de corrélation...),
  sous des noms de clé différents et désynchronisées l'une de l'autre.
- **Ce qui a été fait** : ces constantes vivent désormais dans
  `market_assumptions/default-2026.json` (nouveaux objets `equity.volatility`,
  `real_estate.dynamics`, `rates.risk_free_proxy`, `rates.hull_white`,
  `bond`, `inflation`, `gdp_growth`, `correlations`), lues par les deux
  modules via `load_market_assumptions()` — une seule source, plus de
  désynchronisation possible. `equity_drift` et `real_estate_drift`, qui
  étaient des littéraux indépendants (0,10 et 0,08), sont désormais
  **dérivés** : `risk_free_proxy.mean + risk_premia.<classe>.value` (voir
  `MarketAssumptions.equity_expected_return` /
  `.real_estate_expected_return`), pour que le chemin de génération simple
  reste cohérent avec la séparation risque-neutre/monde réel de l'étape
  1.B.3, même s'il n'a ni courbe EIOPA ni Hull-White. Un `economic_params`
  fourni explicitement par l'appelant reste prioritaire sur cette valeur
  dérivée (comportement inchangé, voir `test_custom_economic_params`).
- **Effet secondaire découvert** : `tests/test_tax_engine.py::create_test_scenarios`
  générait ses scénarios de test avec les valeurs par défaut de
  `ScenarioGenerator`, sans le savoir explicitement. En abaissant
  `equity_drift` (0,10 → 0,08) et surtout `real_estate_drift` (0,08 → 0,045),
  trois tests dont les bornes de sanité (`effective_tax_rate > 0.05`,
  moyenne de rendement positive...) étaient implicitement calibrées sur les
  anciens littéraux se sont mis à échouer sur un échantillon de 10 scénarios
  / 5 ans où la moyenne peut désormais tomber en territoire légèrement
  négatif. Corrigé en fixant explicitement `equity_drift`/`real_estate_drift`
  dans `create_test_scenarios` : ce module teste le calcul de l'impôt, pas
  les hypothèses de marché, et ne doit pas dépendre de leur valeur courante.
- **Lacune ouverte 1** : `rates.hull_white` (a=0,1, sigma=0,01) est marqué
  `status: "placeholder"` — ce sont les anciens littéraux, pas une
  calibration. L'étape 1.B.5 devait les remplacer par une calibration sur
  swaptions réels, mais est différée (voir point 7 ci-dessous).
- **Lacune ouverte 2** : `correlations` reste une extraction fidèle de
  l'ancien littéral, mais **n'est consommé par aucun des deux chemins de
  génération** — `_generate_stochastic` construit sa propre corrélation via
  `CorrelatedRandomGenerator` (matrice n×n interne, ignore
  `config['correlation_matrix']`), et `_generate_simple` n'utilise que des
  poids de corrélation câblés en dur dans ses formules (`0.7 * base_shock +
  0.3 * inflation_shock`, etc.), pas la matrice nommée. C'est une
  configuration validée mais sans effet observable, découverte en
  extrayant cette donnée, pas introduite par cette étape. Hors périmètre :
  la corriger suppose de revoir comment `CorrelatedRandomGenerator` est
  invoqué, un changement de comportement numérique qui mérite sa propre
  étape et sa propre preuve de non-régression.
- **Hors périmètre, non touché** : `GlobalScenarioEngine.generate_optimistic_scenario`
  et `.generate_pessimistic_scenario` gardent leurs propres littéraux ad hoc
  (0,12/0,15 pour l'optimiste, 0,06/0,25 pour le pessimiste...), non dérivés
  de `self.default_params` ni de `market_assumptions` : l'étape 1.B.4 ne
  ciblait que les `default_params` des deux moteurs, pas ces méthodes.

## 7. Étape 1.B.5 (calibration Hull-White sur swaptions) différée faute de données

- **Ouvert le** : 2026-08-28
- **Statut** : différé, en attente de données de marché
- **Contexte** : `legacy/R_scripts/Calib_Taux_Swaptions_V2.R` attend un
  fichier `Prix_swaptions_bloomberg.Rda` (chemin réseau
  `\\intra\partages\...\R4 CALIBRAGE\R4 IN\`) absent de ce dépôt.
  `legacy/excel_files/` ne contient aucune donnée de prix de swaption ; le
  fichier le plus proche par le nom, `Extractions Bloomberg - Calibration
  ESG - ML 1.xlsx`, contient des données d'options sur indice actions
  (feuilles SX5E, V2X), pas des swaptions de taux.
- **Décision** : reporter l'étape 1.B.5 jusqu'à disposer de la donnée de
  marché nécessaire. `rates.hull_white` reste un `placeholder` non calibré
  (point 6 ci-dessus) en attendant.

---

*Dernière mise à jour : 2026-08-28, étape 1.B.4 (extraction des constantes
économiques en donnée versionnée) ; étape 1.B.5 différée.*
