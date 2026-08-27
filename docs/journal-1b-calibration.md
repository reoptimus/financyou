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

---

*Dernière mise à jour : 2026-08-27, étape 1.B.1 (correction du test de
martingalité).*
