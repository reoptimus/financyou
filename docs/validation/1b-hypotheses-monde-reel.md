# Validation 1.B.3 — Primes de risque monde réel

- **Étape** : 1.B.3 (séparation du monde risque-neutre et du monde réel)
- **Rédigé par** : un agent (Claude), sur la branche `phase-1b-calibration`
- **Date** : 2026-08-28
- **Statut des hypothèses** : `draft` dans
  `investment_calculator/market_assumptions/default-2026.json`. Comme pour un régime fiscal
  (voir [ADR 0001](../adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md)), un agent peut
  chercher une valeur, citer sa source et la proposer — il ne peut pas se porter garant d'un
  chiffre engageant pour l'épargne d'un utilisateur. Ce document informe une décision humaine, il
  ne s'y substitue pas.

## Pourquoi ce document existe

Avant cette étape, `black_scholes.py` et `real_estate.py` généraient des rendements sous la seule
mesure risque-neutre : le drift de l'action ne contenait que le taux sans risque stochastique
(Hull-White), sans aucune prime de risque. C'est la mesure correcte pour tester qu'un indice
déflaté reste une martingale (`ScenarioGenerator._test_martingale`) ou pour pricer un produit
dérivé — mais elle est absurde pour projeter le patrimoine d'un épargnant sur 30 ans : sous cette
mesure, un placement en actions ne rapporte, en espérance, pas plus qu'un placement sans risque.
Aucune prime pour le risque pris n'apparaît.

L'étape 1.B.3 sépare explicitement les deux usages :

- le monde **risque-neutre** (`risk_premium=0`) reste utilisé uniquement pour le test de
  martingalité (voir `docs/journal-1b-calibration.md`, entrée « étape 3 ») ;
- le monde **réel** (`risk_premium>0`) alimente désormais `scenarios_df`, c'est-à-dire tout ce qui
  est projeté à l'utilisateur.

La valeur de cette prime n'est pas un paramètre technique : c'est une hypothèse de marché qui
change directement le patrimoine affiché à un épargnant. Elle vit donc dans
`investment_calculator/market_assumptions/default-2026.json`, versionnée et sourcée, au même titre
que le rendement du dividende ou la répartition loyer/appréciation — jamais codée en dur dans le
moteur.

## Primes retenues

| Classe d'actif | Valeur retenue | Fourchette | Méthode / source |
|---|---|---|---|
| Actions | **5,0 %** | 3,5 % – 7,7 % | Convergence entre la prime implicite Damodaran pour la France (5,01 % au 05/01/2026 : 4,23 % de prime marché mature + 0,78 % de prime pays) et la moyenne historique française sur 100 ans citée par Vernimmen (5 %). |
| Immobilier | **1,5 %** | 1,0 % – 2,0 % | Spread direct vs OAT 10 ans, résidentiel/mixte France, source professionnelle Newmark France (via MeilleureSCPI.com). |

Les deux sont des primes **arithmétiques** (moyenne des rendements annuels excédentaires), pas
géométriques (rendement composé équivalent) — la distinction compte sur un horizon de 30 ans : la
prime géométrique est structurellement plus basse à volatilité égale (effet de convexité de la
capitalisation). Utiliser une prime arithmétique dans un drift de diffusion continue, comme fait
ici, est la convention standard en simulation Monte Carlo (c'est la moyenne du drift instantané
qui compte, pas le rendement composé réalisé) ; elle n'est pas directement comparable à un taux de
rendement annonce composé sur 30 ans.

### Actions — détail des sources

- **Damodaran (NYU Stern), Country Default Spreads and Risk Premiums** — estimation implicite
  (méthode du dividende actualisé sur l'indice, pas un sondage), consultée le 2026-08-27. Fournit
  une prime « mature market » (4,23 %) et une prime pays additionnelle pour la France (0,78 %).
  Fourchette basse retenue (3,5 %) : prime mature-market seule, hors prime pays, arrondie.
- **Vernimmen.net**, FAQ « Calcul de la prime de risque », consultée le 2026-08-27 — cite à la
  fois la moyenne historique française sur environ 100 ans (~5 %) et une estimation implicite
  courante plus volatile, plus élevée (~7,7 %), retenue comme fourchette haute.
- **Lacune documentée** (`known_gaps` de `default-2026.json`) : la référence académique la plus
  rigoureuse pour un horizon 30 ans, le Dimson-Marsh-Staunton Global Investment Returns Yearbook,
  n'a pas pu être extraite précisément pour la France lors de cette recherche — seuls des agrégats
  mondiaux ont été confirmés, cohérents avec 5 % mais pas plus précis. À recouper avant validation.

### Immobilier — détail des sources

- **Newmark France, cité par MeilleureSCPI.com**, consultée le 2026-08-27 — un spread résidentiel
  d'environ 150 points de base au-dessus de l'OAT 10 ans. Le marché immobilier professionnel dans
  son ensemble affiche des primes plus dispersées selon le segment (60 à plus de 300 pb) ; 150 pb
  correspond au résidentiel/mixte, pas aux bureaux prime ni aux segments les plus risqués.
- **Lacune documentée** : c'est une source professionnelle secondaire, pas une étude académique ou
  IEIF de premier rang — aucun chiffre agrégé IEIF n'a été retrouvé lors de la recherche. À
  confirmer par recoupement avec les indices IEIF Immobilier d'Entreprise France ou l'Observatoire
  MSCI France avant validation.
- **Réserve structurelle** : `RealEstateModel._generate_auxiliary_rates` a un bug numérique connu
  et distinct (voir `docs/journal-1b-calibration.md`, point 1) qui fait diverger l'indice
  immobilier déflaté sur un horizon de 30 ans, indépendamment de toute prime de risque. La prime
  ci-dessus ne corrige pas cette instabilité — tant qu'elle n'est pas corrigée, une projection
  immobilière monde réel hérite du même défaut numérique que sa contrepartie risque-neutre. C'est
  pourquoi l'illustration immobilière ci-dessous est analytique, pas issue de `RealEstateModel`.

## Effet sur un patrimoine projeté à 30 ans

Pour rendre l'effet concret, la simulation ci-dessous compare, à taux sans risque strictement
identique (même courbe EIOPA France, mêmes chocs aléatoires), un indice de rendement total
actions sous les deux mesures. Reproductible avec `n_scenarios=20000`, `dt=0,25`, `T=30`,
graine 42, courbe `eiopa-fr-2018-04`.

**Actions**, indice de rendement total (dividendes réinvestis), 100 investis en t=0 :

| Mesure | Moyenne à 30 ans | Médiane à 30 ans |
|---|---:|---:|
| Risque-neutre (prime = 0) | 210 | 122 |
| Monde réel (prime = 5,0 %) | 908 | 519 |

Le rapport des moyennes (4,43) est cohérent avec le facteur analytique attendu
`exp(prime × T) = exp(0,05 × 30) = 4,48` (écart résiduel : bruit Monte Carlo à taille d'échantillon
finie). **Ignorer la prime de risque revient donc à sous-estimer d'un facteur supérieur à 4 le
patrimoine actions moyen projeté à 30 ans** — l'ordre de grandeur, pas un détail de second ordre.

**Immobilier**, illustration analytique (`RealEstateModel` non utilisable ici, voir plus haut) :
au taux sans risque zéro-coupon implicite à 30 ans de la courbe EIOPA France (1,91 %), le facteur
de capitalisation passe de `exp(0,0191 × 30) = 1,77` (risque-neutre) à
`exp((0,0191 + 0,015) × 30) = 2,78` (monde réel) — un facteur 1,57, nettement plus modeste que pour
les actions, ce qui reflète la prime de risque immobilière plus faible (1,5 % contre 5 %).

Le script utilisé pour produire ces chiffres :

```python
from investment_calculator.yield_curve import load_yield_curve
from investment_calculator.stochastic_models.hull_white import HullWhiteModel
from investment_calculator.stochastic_models.black_scholes import BlackScholesEquity
from investment_calculator.market_assumptions import load_market_assumptions
import numpy as np

np.random.seed(42)
T, dt, n_scenarios = 30, 0.25, 20000
n_steps = int(T / dt)

curve = load_yield_curve("eiopa-fr-2018-04", dt=dt)
f0t = curve.get_forward_curve(n_steps=n_steps)
P0t = curve.get_bond_prices(n_steps=n_steps)
hw = HullWhiteModel(a=0.1, sigma=0.01, f0t=f0t, P0t=P0t, dt=dt, n_scenarios=n_scenarios, T=T)
hw_res = hw.generate_scenarios()

assumptions = load_market_assumptions()
equity_shocks = np.random.normal(0, 1, (n_scenarios, n_steps))
model = BlackScholesEquity(sigma=0.18, dividend_yield=assumptions.dividend_yield,
                            dt=dt, n_scenarios=n_scenarios, T=T)

index_rn = np.exp(np.cumsum(model.generate_returns(
    hw_res['Rt'], equity_shocks=equity_shocks, risk_premium=0.0
)['total_returns'], axis=1))
index_rw = np.exp(np.cumsum(model.generate_returns(
    hw_res['Rt'], equity_shocks=equity_shocks, risk_premium=assumptions.equity_risk_premium
)['total_returns'], axis=1))
```

## Ce que ce document ne fait pas

- Il ne valide pas les primes retenues comme définitives : le statut reste `draft`, et les
  `known_gaps` ci-dessus listent explicitement ce qui manque pour les faire passer à `validated`
  (recoupement DMS pour les actions, recoupement IEIF/MSCI pour l'immobilier).
- Il ne corrige pas l'instabilité numérique de `RealEstateModel` (étape hors périmètre de 1.B.3,
  documentée dans `docs/journal-1b-calibration.md`).
- Il ne modélise pas de variation de la prime avec l'horizon (court terme vs long terme) ni avec
  le pays — `known_gaps` de `default-2026.json` le signale explicitement.
