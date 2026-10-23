# Inventaire du code R d'origine et ordre de portage

Établi le 2026-10-23 à partir de l'archive complète versée dans
[`legacy/R_Financyou/`](../../legacy/R_Financyou/README.md). Ce document dit ce
que contient le R, ce que le Python couvre déjà, ce qui manque, et dans quel
ordre porter le reste.

Démarche convenue avec seb : pas de second dépôt. On porte module par module
dans le code actuel. Chaque module porté s'accompagne d'une traduction fidèle
du R, qui sert de référence dans les tests, sur les mêmes profils.

## 1. Ce que contient l'archive

Le pipeline d'origine a quatre étages. Les noms sont ceux des répertoires.

| Étage | Répertoire | Rôle | Scripts principaux |
|---|---|---|---|
| GSE | `GSE/2. Organisation scripts/` | Calibration et diffusion des scénarios économiques : taux Hull-White, actions Black-Scholes, immobilier, inflation, déflateur, aléas corrélés | `R4 CALIBRAGE/` (swaptions, f0(t), actions, immobilier), `R2 CUBE/R2 FCT/` (`HullWhite_*`, `ActionBS_*`, `ImmoHW_*`, `Inflation_V1`, `Deflator_V2`), `R3 CUBE ALEA/cubealea_V1…V5`, `R1 MEFCUBE/MEFCUBE*` (mise en forme du cube), validation martingale |
| GSE+ | `GSE+/R2 CUBE+/` | Rendements avant impôt des produits accessibles à un particulier | `Produits_placements.R`, `Oblig_V1.R`, `Oblig_credit_spread_V1.R` (défauts et spreads par notation, matrices de transition S&P) |
| GSE++ | `GSE+/R1 CUBE++/` | Rendements après frais, impôts et crédit | `Earn_Aft_Int_TaxesV2.R`, `Earn_Aft_Int_TaxesV3.R`, `Formation_GSE++.R` |
| MOCA | `MOCA/` | Moteur de conseil : flux du foyer, engagements, découpage en tranches, optimisation, assemblage | `Lancement_MOCA.R` (enchaînement de janvier 2020), `FCT/Exp_finance_hist.R`, `FCT/Assembl_engagements.R`, **`FCT/Reoptimus_striping.R`**, `FCT/Script_Bootstrap_V3/V4/V5_quick.R`, `FCT/gen_alpha_optim.R` et `_V2`, `FCT/Assembl_invest.R` et `V2` |
| Application | `ShinyR/BetaV1/Financyou/` | Application Shiny, version la plus récente du moteur (mai à décembre 2020) | `server.R`, `ui.R`, `global.R` ; `Data_Log/FCT_Global/` (moteur) ; `Data_Log/FCT_A/` (assemblage et graphiques) ; `Data_Log/Data/` (tables) |

### Le script des tranches est retrouvé

Le script qui produit `Strip_invest.Rda` est **`MOCA/FCT/Reoptimus_striping.R`**
(fonction `stripping`, janvier 2020). Une version adaptée à l'application est
dans `ShinyR/BetaV1/Financyou/Data_Log/FCT_A/Reoptimus_striping.R` : elle
renvoie la matrice des tranches au lieu de l'écrire sur disque.

Ce qu'il fait :

1. Il interpole linéairement la courbe de capital cumulé, avec un pas de
   temps assez fin pour qu'aucune marche annuelle ne saute plus d'une tranche
   de `pas_E` euros (5 000 € dans `Lancement_MOCA.R`).
2. Il ramène la courbe à un escalier de niveaux de tranche, puis la prolonge
   en montée depuis zéro et en descente jusqu'à zéro.
3. Il parcourt les maxima et minima locaux. Pour chaque niveau `j`, il note la
   date d'entrée et la date de sortie de la tranche.
4. Il recolle les segments contigus d'un même niveau.

Le résultat `Tr1` a trois colonnes : date de début, date de fin, numéro de
tranche. `MOCA/OUT/Strip_invest.Rda` en garde un exemple (41 tranches,
`pas_E` = 5 000). La courbe d'entrée de cet exemple n'est pas conservée. Le
test de non-régression devra donc partir d'une courbe construite pour le test,
passée à la traduction fidèle et au portage.

### Le moteur de l'application (`Data_Log/FCT_Global/`)

C'est la partie la plus aboutie, et celle qui manque le plus au Python.

| Script | Rôle |
|---|---|
| `fct_chrono_flux.R` | Le tableau chronologique du foyer (`tab_chrono`), année par année. Revenus des deux adultes, retraite (`tab_retraite`, `tab_coef_retraite`), pensions, loyer, parts fiscales hors projets et avec projets, impôt sur le revenu, dépenses courantes par unité de consommation (`Part_conso_foyer` : échelles Oxford et OCDE), crédits (principal et intérêts), crédits d'impôt, épargne libre, taux d'endettement et capacité d'emprunt. |
| `Exp_proj_hist.R` | Un projet à six champs (début, versement initial, versement annuel, durée, sortie, pente), daté, en flux annuels. |
| `fct_imp_IR.R` | Impôt par tranches à partir du quotient familial (`tab_IR`). |
| `fct_crd_flux.R` | Un crédit à annuités constantes en flux de principal et d'intérêts. |
| `fct_crd_imp_flux.R` | Flux d'un crédit d'impôt (Pinel, Malraux…) depuis `tab2_crd_imp`. |
| `CF_cumul_avec_proj.R` | La trésorerie disponible, avec ou sans projets. |
| `fct_contraintes_eur.R` | Les engagements en euros par placement : crédits en cours, placements existants bloqués, supports partagés (assurance vie euros/UC). |
| `fct_prod_soltot.R` | L'allocation optimale par horizon, interpolée entre les deux plus proches voisins d'une grille précalculée (`List_alpha_approx`, `Tab_alpha_approx`, produits par `gen_alpha_optim_V2.R`), puis recalée sur les contraintes exactes. |
| `Lancement_MOCA_A.R` | `MOCA()` : contraintes, flux cumulé, allocation, découpage en tranches, assemblage. |
| `fct_discret_optim.R`, `fct_optim_interm.R`, `fct_recalcul_revenu.R`, `modif_chrono_flux_plc.R`, `modif_tabl_plac.R` | La discrétisation des achats immobiliers à crédit. L'optimum continu propose une part de crédit. On cherche alors la date et l'annuité qui couvrent le mieux cette part, puis on réinjecte le crédit dans `tab_chrono`. |
| `fct_MOCAdre.R` | La boucle externe : avec et sans projets, et tant qu'un crédit reste à discrétiser. |
| `FCT_A/Assembl_investV3.R` | L'assemblage : chaque tranche reçoit l'allocation optimale à sa durée, à partir de sa date d'entrée. Les rendements par scénario sont cumulés à terme et en valeur liquidative. |
| `FCT_A/fct_KPI.R`, `FCT_A/Visu_*.R` | Indicateurs et graphiques : revenus, dépenses, impôts, taux d'endettement maximal, liquidité minimale. |

## 2. Par rapport à `legacy/R_scripts/`

Les 58 scripts de `legacy/R_scripts/` sont tous dans l'archive, à l'identique,
à un des emplacements d'origine. Trois noms existent en plusieurs copies qui
diffèrent :

- `Earn_Aft_Int_TaxesV3.R` : la copie de `R_scripts` est celle de
  `GSE+/R1 CUBE++/`. Celle de l'application prend en entrée le tableau des
  placements du foyer et le barème `tab_IR` au lieu de fichiers fixes.
- `F_Rdtcumul.R` : la copie de `GSE/…/R1 MEFCUBE/` diffère des trois autres.
- `F_Vacisek1.R` : la copie de `GSE/…/Fonctions globales/` diffère.

Ce que l'archive apporte de neuf : `Reoptimus_striping.R`, les trois versions
du bootstrap de Michaud (`Script_Bootstrap_V3`, `V4`, `V5_quick`),
`gen_alpha_optim_V2.R`, `Lancement_MOCA.R`, `Earn_Aft_Int_TaxesV2.R`, tout le
moteur de l'application (`FCT_Global/`, `FCT_A/`) et ses tables (`Data/`), les
versions 1 à 4 du cube aléatoire et les scripts de validation.

## 3. Couverture par le Python actuel

| Module R | Équivalent Python | État |
|---|---|---|
| Calibration Hull-White (swaptions, f0(t)) | `stochastic_models/calibration.py`, `swaption_surface`, `yield_curve.py` | Couvert |
| Diffusion taux, actions, immobilier, aléas corrélés | `stochastic_models/hull_white.py`, `black_scholes.py`, `real_estate.py`, `correlation.py`, `modules/scenario_generator.py` | Couvert |
| Inflation, déflateur (`Inflation_V1`, `Deflator_V2`) | `scenario_generator.py` | Partiel : le déflateur Python est un simple facteur d'actualisation. |
| GSE+ : produits de placement (`Produits_placements.R`, `Oblig_V1.R`) | `modules/placements.py` (fonds euros adossé à l'actif général, obligations en valeur comptable) | Couvert, et refondu en octobre 2026 |
| GSE+ : obligations notées, défauts et spreads (`Oblig_credit_spread_V1.R`) | — | Manquant |
| GSE++ : frais et impôts (`Earn_Aft_Int_Taxes*`) | `modules/net_returns.py` et `tax_regimes/` | Couvert pour les enveloppes. Manquent : immobilier à crédit, crédits d'impôt (Pinel…), tranche marginale par foyer. |
| Markowitz par horizon (`gen_alpha_optim.R`) | `placement_optimizer.optimize_horizon` | Couvert |
| Rééchantillonnage de Michaud (`Script_Bootstrap_V5_quick.R`) | — | Manquant. Le script était absent : la docstring de `placement_optimizer.py` le signale. |
| Grille approchée (`gen_alpha_optim_V2.R`, `fct_prod_soltot.R`) | — | Non porté. C'était une accélération pour shinyapps.io : à ne porter que si l'optimisation directe est trop lente. |
| Projets et flux du foyer (`Exp_finance_hist.R`, `Exp_proj_hist.R`, `fct_chrono_flux.R`) | — | Manquant : une seule épargne mensuelle, un seul horizon. |
| Parts fiscales et impôt sur le revenu (`fct_imp_IR.R`, parts dans `fct_chrono_flux.R`) | — | Manquant |
| Crédits en cours (`fct_crd_flux.R`, `Assembl_engagements.R`) | — | Manquant |
| Engagements en euros (`fct_contraintes_eur.R`) | Contraintes actions et obligations du profil (`wrapper_allocation.py`) | Partiel : contraintes de profil, pas d'engagements datés. |
| Découpage en tranches (`Reoptimus_striping.R`) | — | Manquant. `time_series_slicer` est un découpeur générique, pas cet algorithme. |
| Assemblage multi-horizons (`Assembl_investV2.R`, `V3`) | — | Manquant |
| Achat immobilier à crédit (`fct_discret_optim.R` et suivants) | — | Manquant |
| Indicateurs et graphiques (`fct_KPI.R`, `Visu_*`) | `modules/reporting.py` | Partiel |
| Application Shiny | `web_ui/app_enhanced.py` | À ne pas porter : on reprend le format des projets dans le formulaire. |

## 4. Valeurs codées en dur dans le R

Le R mêle des paramètres au code. Ces valeurs ne seront **pas** recopiées
telles quelles. Les règles du dépôt l'interdisent : aucune valeur inventée,
aucune fiscalité dans le code.

- **Fiscalité**, à mettre dans le régime, sourcée et validée par une personne :
  - le barème `tab_IR` (0 / 10 064 / 25 659 / 73 369 / 157 806 €, soit le
    barème des revenus 2020) ;
  - les crédits d'impôt de `tab2_crd_imp` (Pinel 2 % par an sur 9 ans,
    plafond 300 000 € ; Malraux) ;
  - l'abattement de 10 % pour frais (`fct_chrono_flux.R`) ;
  - les parts d'enfant à 0,5 puis 1 à partir du troisième, jusqu'à 20 ans ;
  - `Tranche_marginale_IR.csv`, `Abattement pluesvalues.csv`, `SurtaxePVimmo.csv`.
- **Hypothèses de marché**, à sourcer et à passer en paramètres :
  - rendement locatif de 2,5 % (Pinel) ou 4 % (locatif), loyer retenu à 85 %
    (`fct_recalcul_revenu.R`) ;
  - montant minimal d'un achat immobilier, 200 000 €, marqué « à vérifier ! »
    dans le code ;
  - apport minimal de 10 %.
- **Règles bancaires**, à sourcer : taux d'endettement maximal de 33 % et prise
  en compte des revenus locatifs à 75 % (`fct_chrono_flux.R`).
- **Tables de profil**, à sourcer : taux de remplacement à la retraite par
  catégorie (`tab_retraite`), échelles d'unités de consommation
  (`Part_conso_foyer`), allocations familiales.

## 5. Ordre de portage proposé

Une PR par étape. Chaque étape commence par la traduction fidèle du R dans
`tests/` (référence), puis porte le module et compare les deux sur les mêmes
entrées.

1. **Projets et courbe de capital.** Porter `Exp_proj_hist.R` (projet à six
   champs) et la somme cumulée de `Exp_finance_hist.R` : épargne de départ,
   épargne annuelle et projets donnent le capital disponible par année.
   Aucune fiscalité. C'est l'entrée de tout le reste.
2. **Découpage en tranches.** Porter `Reoptimus_striping.R`. On compare au R
   traduit sur des courbes de test : montée simple, creux dû à un projet,
   plusieurs creux. La taille de tranche est un paramètre, pas une constante.
3. **Assemblage multi-horizons.** Porter `Assembl_investV3.R` : chaque tranche
   reçoit `optimize_horizon` à sa durée, puis on réassemble. L'argent d'un
   projet est alors placé à l'horizon du projet. C'est le changement qui se
   verra le plus pour l'utilisateur.
4. **Rééchantillonnage de Michaud.** Porter `Script_Bootstrap_V5_quick.R`
   dans `placement_optimizer`. Cela stabilise les allocations par tranche,
   qui reposent sur moins de données que l'allocation unique d'aujourd'hui.
5. **Formulaire des projets.** Les projets au format d'origine dans
   `web_ui/app_enhanced.py`.
6. **Parts fiscales et impôt sur le revenu.** Barème et quotient familial
   dans le régime (données à sourcer, puis validées par seb), puis
   `fct_imp_IR.R` et le calcul des parts. On en tire la tranche marginale du
   foyer, qui ne sert qu'aux produits imposés au barème.
7. **Flux complet du foyer.** Le reste de `fct_chrono_flux.R` : revenus et
   retraite, dépenses par unité de consommation, loyer, crédits en cours
   (`fct_crd_flux.R`), épargne libre, taux d'endettement. Ensuite les
   engagements datés (`fct_contraintes_eur.R`). Les tables de profil doivent
   être sourcées avant.
8. **Immobilier à crédit.** `fct_discret_optim.R` et la suite, avec les
   crédits d'impôt. Cela dépend du modèle immobilier et des hypothèses de la
   section 4. C'est la dernière étape et la plus lourde.

Hors de cet ordre, à décider plus tard : les obligations notées avec défauts
(`Oblig_credit_spread_V1.R`) et la grille approchée (`fct_prod_soltot.R`).

## 6. Exécuter le R de référence

R n'est pas installé dans l'environnement de travail actuel. Les références
seront donc des traductions fidèles en Python, ligne à ligne, des fonctions R
pures (`stripping`, `Exp_fin`, `Flux_crd`, `fct_flux_IR`…). Pour les comparer
à R lui-même, il faudrait installer R dans la CI et produire des sorties de
référence. C'est possible pour les fonctions sans accès disque, mais ce n'est
pas nécessaire pour avancer.
