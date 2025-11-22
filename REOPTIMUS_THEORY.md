# Réoptimus - Théorie de l'Optimisation de l'Épargne des Particuliers

## Vue d'ensemble

Ce document présente les fondements théoriques et mathématiques du système Réoptimus, utilisé dans FinancYou pour optimiser l'épargne et les investissements des particuliers. Le principe repose sur une modélisation complète des flux financiers, de la fiscalité, et de l'optimisation de portefeuille selon la théorie de Markowitz.

---

## Table des matières

1. [Principe d'optimisation de l'épargne des particuliers](#1-principe-doptimisation-de-lépargne-des-particuliers)
2. [Modélisation de la propriété du lieu d'habitation](#2-modélisation-de-la-propriété-du-lieu-dhabitation)
3. [Calcul de l'optimum de l'investissement d'un particulier](#3-calcul-de-loptimum-de-linvestissement-dun-particulier)
4. [Variables du placement d'un particulier](#4-variables-du-placement-dun-particulier)
5. [Rendements des placements](#5-rendements-des-placements)
6. [Frais, Imposition et Inflation](#6-frais-imposition-et-inflation)
7. [Optimisation de Markowitz](#7-optimisation-de-markowitz)
8. [Appétence au risque et horizon de placement](#8-appétence-au-risque-et-horizon-de-placement)
9. [Budget et dépenses prévisionnels de l'utilisateur](#9-budget-et-dépenses-prévisionnels-de-lutilisateur)
10. [Découpage du prévisionnel des cash-flows BaseLine](#10-découpage-du-prévisionnel-des-cash-flows-baseline)
11. [ALM - Relation entre résultats et optionalité](#11-alm---relation-entre-résultats-et-optionalité)
12. [GSE - Générateur de Scénarios Économiques](#12-gse---générateur-de-scénarios-économiques)
13. [Temps de calcul et optimisation](#13-temps-de-calcul-et-optimisation)

---

## 1. Principe d'optimisation de l'épargne des particuliers

Le système Réoptimus vise à optimiser les flux financiers d'un particulier dans leur ensemble (salaire, frais, impôts, retraites) pour une répartition inter-temporelle longue (de 10 à 30 ans). L'approche tient compte des spécificités suivantes :

- Les flux futurs ne sont pas connus avec certitude
- L'objectif de transmission patrimoniale (legs) tout en assurant une disponibilité des liquidités
- L'impossibilité de faire faillite (contrairement à une entreprise)

---

## 2. Modélisation de la propriété du lieu d'habitation

### Hypothèses de base

On part du principe qu'à **t₀**, l'investisseur possède un capital liquide net de taxes. Il n'est donc ni locataire, ni propriétaire mais dispose de son capital pour arbitrer entre ces deux situations.

### Principe du loyer universel

**Tout le monde paye un loyer** (virtuel ou réel selon que l'on soit propriétaire ou non) pour pouvoir se loger. Ce loyer dépend :

- Des prétentions de l'utilisateur (niveau de vie souhaité)
- Du prix d'achat correspondant à sa volonté d'habitat

**Important** : Le lien entre loyer acceptable et prix d'achat acceptable est personnel et ne correspond pas nécessairement au marché.

### Traitement dans l'optimisation

Par défaut, l'investisseur est considéré comme **locataire avec investissement du surplus**. Si l'achat est privilégié :

- La partie loyer est réaffectée au rendement de l'actif "immobilier propriétaire habitant"
- Le loyer réaffecté est celui de l'habitation achetée (et non celui du loyer si l'on n'achète pas)

Cette approche permet de comparer équitablement les deux stratégies (location vs. achat) sur la même base financière.

---

## 3. Calcul de l'optimum de l'investissement d'un particulier

### Spécificités de l'investisseur particulier

Le particulier est un investisseur particulier car :

- Il cherche à optimiser ses flux financiers dans leur ensemble (salaire, frais, impôts, retraites…) pour une répartition inter-temporelle longue (de 10 à 30 ans)
- Il ne connaît pas ses flux futurs avec certitude
- Il souhaite léguer tout en assurant une disponibilité "au cas où"
- Il n'est pas prêt à déposer le bilan ou faire banqueroute (contrairement à une entreprise)

---

## 4. Variables du placement d'un particulier

Les variables principales sont :

| Variable | Description |
|----------|-------------|
| **A₀** | Apport initial à t₀ |
| **S** | Salaire (exclus les rentrées annexes type loyer issu du capital) |
| **%S** | Pourcentage de salaire (hors loyers perçus) consacré à l'épargne |
| **L** | Loyer payé aujourd'hui (si locataire) ou dividende pour les actions |
| **Cap** | Capital net en possession (après revente virtuelle et règlement des frais et taxes) |
| **E₀** | Emprunt en cours à t₀ (Capital restant dû) |

---

## 5. Rendements des placements

### Types de rendements étudiés

Les différents types de rendement de placements sont :

| Type | Notation | Description |
|------|----------|-------------|
| **Placement sans risque court terme** | R_srct | Type Livret A |
| **Placement risqué court terme** | R_rct | Type actions |
| **Obligations** | R_obl | Obligations d'État ou Corporate |
| **Immobilier d'habitation propre** | R_immo_p | Rendement d'un placement immobilier habité par le propriétaire |
| **Immobilier d'investissement** | R_immo_i | Rendement d'un placement immobilier mis en location |
| **Évolution des prix de l'immobilier** | R_immo | Rendement dû uniquement à l'évolution des prix |

### Formules générales

Tous les placements sont soumis à imposition et taxes selon les mêmes principes et outils fiscaux.

#### Pour un placement simple capitalisé

**Flux unique à t=0 :**

```
f_H = A₀ · R_srct(0→H)
```

**Flux annuel constant à partir de t=0 :**

```
f_H = a₀ · Σ(i=0 to H-1) R_srct(i→H)
```

Où :
- `a₀` : somme fixe investie annuellement
- Cette formule concerne les supports sécables (achetables par morceaux de montants continus)
- Ne s'applique pas à l'immobilier qui doit être acheté "en une fois"

#### Cas particulier de l'immobilier avec prêt

Pour l'immobilier, la particularité vient du **prêt à remboursement constant**. Le capital est constitué instantanément au moment du prêt puis remboursé par montants constants.

Avec **τ**, le taux d'emprunt bancaire :

```
f_H = a⁰ · [(1-(1+τ)^(-N))/τ] · [R_immo(0→H) - (1-(1+τ)^(-N+H))/(1-(1+τ)^(-N))]
```

Où :
- `N` : nombre d'années d'emprunt
- `H` : horizon d'évaluation du placement

### Notation dans la suite

Nous noterons dans la suite :

**Pour investissement progressif :**
```
f_H = a^invest · Σ(i=0 to H-1) R_srct(i→H)
```

**Pour investissement via prêt :**
```
f_H = a^prêt · [(1-(1+τ)^(-N))/τ] · [R_immo(0→H) - (1-(1+τ)^(-N+H))/(1-(1+τ)^(-N))]
```

### Loyers perçus dans l'investissement locatif

Si on ajoute les loyers perçus dans le cadre d'un investissement locatif :

```
f_H = αL · σL · Σ(i=0 to H-1) I(i→H) = αL · Σ(i=0 to H-1) σL_i
```

**Note importante** : On ne considère pas le réinvestissement des loyers perçus dans l'immobilier. On considère qu'ils sont conservés au taux monétaire. Les loyers ne sont donc pas capitalisés.

### Formule complète avec loyers

```
f_H = A₀ · [R_immo(0→H) + αL · Σ(i=0 to H-1) σL_i]
    + a^prêt · [(1-(1+τ)^(-N))/τ] · [R_immo(0→H) - (1-(1+τ)^(-N+H))/(1-(1+τ)^(-N)) + αL · Σ(i=0 to H-1) σL_i]
```

Avec :
- **σL** : rendement locatif brut attendu
- **αL** : coefficient de dégrèvement des frais divers de location (~70%, soit ~30% pour réparation et entretien)
- **σL_i** : loyer de la période i pour l'indexation des loyers hors inflation monétaire

### Symbole de Kronecker δ

En utilisant le symbole de Kronecker :
- **δ = 0** si immobilier en habitation propre
- **δ = 1** si immobilier d'investissement mis en location

**Important** : Dans un investissement où l'on habite, on peut considérer que le loyer nous est versé (équivalent à retirer le loyer du budget), donc **δ = 1** même si l'on habite le logement. **δ = 0** uniquement pour l'achat d'une résidence secondaire.

Cependant, pour les aspects fiscaux (abattements d'impôts, imposition de revenus complémentaires), il faut créer un **δ2** pour distinguer :
- **δ2 = 1** : location à autrui (ou autres supports que l'immobilier)
- **δ2 = 0** : "location" à soi (habitation propre)

### Autres investissements

Pour les investissements actions, obligations ou assurance vie :
- Les dividendes sont intégrés aux rendements
- Dans tous les cas **δ = 0**
- δ est donc l'**indicateur de versement de dividendes**

### Split en deux termes

Le rendement peut être décomposé en deux termes :

```
f_H = A₀ · [RA_immo] + a^prêt · [Ra_immo]
```

Où :
- **RA** : rendements associés à la partie de l'apport lors de l'achat
- **Ra** : rendements de la partie associée à l'emprunt et aux annuités de remboursement

### Retour sur l'équivalence d'un rendement annuel

Les rendements calculés sont cumulés entre t₀ et la durée du rendement observé. Pour revenir à des rendements annuels équivalents :

**Pour RA (investissement à horizon H) :**
```
RA_immo_annuel_H = sign(RA_immo) · ᴴ√|RA_immo|
```

**Pour Ra (investissement répété tous les ans) :**

On cherche la solution x de :
```
(1-x^(H+1))/(1-x) = |Ra_immo_H - 1| + 1
```

C'est une racine réelle d'un polynôme de degré (H+1) dont on connaît une approximation (entre 0 et 2 environ). Cette solution est trouvée numériquement.

**Note** : Ce calcul doit être fait pour tous les scénarios économiques et peut ralentir l'algorithme.

---

## 6. Frais, Imposition et Inflation

### Frais d'acquisition

Les frais d'acquisition en pourcentage sont notés **Fees%_srct** et sont directement prélevés sur les rendements R.

### Imposition

L'imposition utilisée est celle en vigueur (actuellement 2016 dans le document original). L'imposition est toujours payée :
- À la fin du placement
- Sur la plus-value uniquement
- Après abattement

#### Pour un flux unique à t=0

```
f_H = A₀ · [R_srct(0→H) · (1-(1-Ab)·τ_imp) + (1-Ab)·τ_imp]
```

Avec :
- **Ab** : taux d'abattement
- **τ_imp** : taux d'imposition sur le revenu marginal

#### Pour un flux annuel constant

```
f_H = a^invest · [Σ(i=0 to H-1) R_srct(i→H) · (1-(1-Ab)·τ_imp) + H·(1-Ab)·τ_imp]
```

**Note** : Beaucoup de produits comme le PEA et l'assurance vie exonèrent de l'IR après un délai suffisant (ex : 5 ans pour le PEA, 8 ans pour l'assurance vie).

### Intégration des frais d'acquisition

Les frais d'acquisition sont déduits des rendements :

```
f_H = a^invest · [Σ(i=0 to H-1) (R_srct(i→H)/(1+Fees%_srct)) · (1-(1-Ab)·τ_imp) + H·(1-Ab)·τ_imp]
```

Ou encore :

```
f_H = a^invest · [Σ(i=0 to H-1) R_srct(i→H) · ((1-(1-Ab)·τ_imp)/(1+Fees%_srct)) + H·(1-Ab)·τ_imp]
```

### Inflation et euros courants vs constants

Nous considérons des **euros courants** et des **taux nominaux** :
- Les sommes considérées (annuités) sont des euros de l'année de référence
- Les taux utilisés (emprunt bancaire, imposition, rendement) sont tous nominaux

Une fois le calcul de rendement réalisé, on actualise de l'inflation pour connaître le résultat en euros constants.

**Important** : Les sommes investies (annuités) sont nominales. On ne considère pas que les annuités suivent automatiquement l'inflation. Le delta entre l'annuité consentie aujourd'hui et l'annuité augmentée de l'inflation dans le futur n'est pas considéré.

### Cas de l'immobilier

Pour l'immobilier, les frais d'acquisition (notaire + agence) donnent :

```
f_H = A₀ · [(R_immo/(1+Fees%_immo)) + δ·αL·Σ(i=0 to H-1) σL_i]
    + a^prêt · [(1-(1+τ)^(-N))/τ] · [(R_immo/(1+Fees%_immo)) - (1-(1+τ)^(-N+H))/(1-(1+τ)^(-N)) + δ·αL·Σ(i=0 to H-1) σL_i]
```

### Taxe foncière

Si on ajoute la taxe foncière annuelle calculée sur :
- Base d'un équivalent de loyer annuel
- Abattement de 50% (pour habitation)
- Coefficient de la ville (~15% mais de 1% à 50%)

Alors :

```
f_H = A₀ · [(R_immo/(1+Fees%_immo)) + (δ·αL - (1-Ab_TF)·Taux_TF_Ville)·Σ(i=0 to H-1) σL_i]
    + a^prêt · [(1-(1+τ)^(-N))/τ] · [(R_immo/(1+Fees%_immo)) - (1-(1+τ)^(-N+H))/(1-(1+τ)^(-N))
    + (δ·αL - (1-Ab_TF)·Taux_TF_Ville)·Σ(i=0 to H-1) σL_i]
```

Avec :
- **Ab_TF** : abattement pour les impôts fonciers (50% pour les habitations - terrain bâti)
- **Taux_TF_Ville** : coefficient d'imposition pour les impôts fonciers de la commune
- Rappel : **δ=1** pour mise en location ET habitation propre ; **δ=0** uniquement pour habitation secondaire

**Note** : Il n'y a pas d'équivalent de la taxe foncière pour les autres supports, ces deux taux sont donc nuls.

### Imposition sur les loyers

Sont déductibles :
- Les frais
- Les intérêts d'emprunts

**Part des loyers déductibles suite aux frais :**
```
[A₀ + a^prêt·((1-(1+τ)^(-N))/τ)]·(1-αL)·Σ(i=0 to H-1) σL_i
```

**Intérêts d'emprunt l'année n :**
```
a^prêt·(1-(1+τ)^(-N+n))
```

**Intérêts d'emprunts sur l'ensemble des périodes :**
```
Σ(i=0 to H-1) a^prêt·(1-(1+τ)^(-N+i)) = a^prêt·[H + (1-(1+τ)^H)/(τ·(1+τ)^N)]
```

**Somme totale déductible :**
```
A₀·(1-αL)·Σ(i=0 to H-1) σL_i
+ a^prêt·[((1-(1+τ)^(-N))/τ)·(1-αL)·Σ(i=0 to H-1) σL_i + H + (1-(1+τ)^H)/(τ·(1+τ)^N)]
```

### Gain total de l'investissement immobilier

Avec **%IR** et **%CS** les taux d'imposition de l'impôt sur le revenu et des charges sociales :

```
f_H = A₀·[(R_immo/(1+Fees%_immo)) + Σ(i=0 to H-1) σL_i·[δ·(αL - (Taux_IR + Taux_CS)·(2αL-1)) - (1-Ab_TF)·Taux_TF_Ville]]
    + a^prêt·{((1-(1+τ)^(-N))/τ)·[(R_immo/(1+Fees%_immo)) - (1-(1+τ)^(-N+H))/(1-(1+τ)^(-N))
    + Σ(i=0 to H-1) σL_i·[δ·(αL - (Taux_IR + Taux_CS)·(2αL-1)) - (1-Ab_TF)·Taux_TF_Ville]]
    + δ·(Taux_IR + Taux_CS)·[H + (1-(1+τ)^H)/(τ·(1+τ)^N)]}
```

### Traitement fiscal des autres supports

#### Immobilier de logement propre
Exonération de la plus-value de revente (principal avantage fiscal)

#### PEA (Plan d'Épargne en Actions)
- Non soumis à l'IR sur les intérêts après 5 ans
- Soumis uniquement aux CS (Charges Sociales) sur les intérêts lors de la sortie
- Imposition sur les plus-values de revente

#### Assurance vie
- Taux libératoire forfaitaire dégressif selon les années de détention :
  - 30% < 5 ans
  - 15% entre 5 et 8 ans
  - 7,5% au-delà de 8 ans
- Abattement de 9 200€/an par foyer (ou 4 600€ pour une personne seule)
- 15,5% de CS prélevés chaque année sur les intérêts
- Pour simplifier le calcul, on considère que l'ensemble abattement/IR et CS sont prélevés lors de la sortie

#### Autres supports
- Soumis à l'IR marginal sans abattement
- CS de 15,5% sur les plus-values de revente

### Imposition sur la plus-value de revente

**Plus-value brute :**
```
[A₀ + a^prêt·((1-(1+τ)^(-N))/τ)]·[(R_immo/(1+Fees%_immo)) - 1]
```

**Impôt sur la plus-value nette pour le calcul de l'IR :**
```
[A₀ + a^prêt·((1-(1+τ)^(-N))/τ)]·[(R_immo/(1+Fees%_immo))·(1-Ab_IR) - 1]·δ(Pv+)·PV_IR
```

Avec :
- **δ(Pv+) = 0** si la plus-value brute ≤ 0 (donc si (R_immo/(1+Fees%_immo)) ≤ 1)
- **δ(Pv+) = 1** sinon

**Gain après déduction de l'impôt sur la plus-value :**

```
[A₀ + a^prêt·((1-(1+τ)^(-N))/τ)]·(R_immo/(1+Fees%_immo))
·[1 - δ2·{(1-Ab_IR)·δ(Pv+)·PV_IR + δ(Pv+)·PV_IR·(1+Fees%_immo)/R_immo}]
```

**Note** : Cela ne s'applique pas dans le cas d'une habitation propre (c'est le seul cas où δ2=0).

### Formule complète avec charges sociales et surtaxe

En ajoutant les charges sociales et la surtaxe pour les plus-values immobilières (> 50 000€) :

```
[A₀ + a^prêt·((1-(1+τ)^(-N))/τ)]·(R_immo/(1+Fees%_immo))
·[1 - δ2·δ(Pv+)·{(1-Ab_IR)·(δ(Pv+)·PV_IR + δ_PV·Taux_Surtaxe) - (1-Ab_CS)·Taux_CS
+ (PV_IR + Taux_CS + δ_PV·Taux_Surtaxe)·(1+Fees%_immo)/R_immo}]
```

Avec :
- **δ_PV = 1** si plus-value nette > Limite surtaxe
- **Taux_Surtaxe** = fonction de la plus-value (voir barème progressif)
- **δ(Pv+) = 0** si plus-value brute ≤ 0
- **δ2 = 1** pour location à tierce personne ou autres supports
- **δ2 = 0** pour habitation propre
- **δ = 0** pour habitation secondaire et autres supports que l'immobilier (sinon = 1)

### Traitement pour les autres supports

#### PEA
- **δ_PV = 0** (pas de surtaxe)
- Exonération d'IR après 5 ans
- Seules les CS sont dues

#### Assurance vie
- **PV_IR** égal au forfait libérataire (voir ci-dessus)
- Application d'un abattement
- Pas d'abattement sur les CS

#### Autres supports
- Application de l'IR marginal
- CS sans abattements

### Formule générale finale pour l'immobilier

```
f_H = A₀·[RA_immo] + a^prêt·[Ra_immo]
```

Où :

```
RA_immo = (R_immo/(1+Fees%_immo))·[1 - δ(Pv+)·δ2·{(1-Ab_IR)·(PV_IR + δ_PV·Taux_Surtaxe)
        - (1-Ab_CS)·Taux_CS + (PV_IR + Taux_CS + δ_PV·Taux_Surtaxe)·(1+Fees%_immo)/R_immo}]
        + Σ(i=0 to H-1) σL_i·[δ·(αL - δ2·(Taux_IR + Taux_CS)·(2αL-1)) - (1-Ab_TF)·Taux_TF_Ville]
        - αFE·Σ(i=1 to H) R_immo(0→i)
```

```
Ra_immo = ((1-(1+τ)^(-N))/τ)·[RA_immo - (1-(1+τ)^(-N+H))/(1-(1+τ)^(-N))]
        + δ·δ2·(Taux_IR + Taux_CS)·[H + (1-(1+τ)^H)/(τ·(1+τ)^N)]
```

Où **αFE** est le taux de frais sur encours (ex : assurance vie).

**Lorsque le prêt est entièrement remboursé (H > N) :**

```
Ra_immo(H>N) = ((1-(1+τ)^(-N))/τ)·RA_immo
             + δ·δ2·(Taux_IR + Taux_CS)·[N + (1-(1+τ)^N)/(τ·(1+τ)^N)]
```

### Investissements annualisés

Concernant les investissements annualisés **a^invest**, ils peuvent être considérés comme des investissements unitaires à des périodes différentes A₀, A₁, A₂, …, A_H.

Il n'est donc pas nécessaire d'évaluer les rendements pour ces investissements annuels séparément, car ils sont calculés au travers des rendements d'investissements unitaires pour tous les débuts de périodes jusqu'à l'horizon H.

**Approche de calcul** : Il suffit de calculer les rendements pour des supports :
- Soit payés comptant
- Soit achetés comptant mais via un prêt

Ce sont donc **deux séries de rendements** qui seront calculées pour chaque support et pour chaque période de i→H (avec 0 < i < H).

Cette technique du calcul du rendement est utilisable pour tous les types de placements. Le split en deux termes distincts (RA et Ra) permet d'optimiser indépendamment :
- L'apport en numéraire
- Les flux issus d'un emprunt

---

## 7. Optimisation de Markowitz

### Principe

Pour optimiser le portefeuille des placements disponibles à un particulier en utilisant la théorie du portefeuille de Markowitz, il faut synthétiser chaque placement par :

1. **Rendement réel moyen** : incluant les frais et impôts, joué sur les scénarios du GSE
2. **Volatilité** : issue des mêmes données que pour le rendement

### Méthode de Michaud (Bootstrap)

Afin de désensibiliser les résultats, il est souhaitable de :

1. Recalculer les rendements et volatilités sur une sous-partie des projections (bootstrap)
2. Recalculer pour chaque sous-ensemble la répartition optimum par la méthode de Markowitz
3. Le portefeuille retenu sera la **moyenne des résultats obtenus**

Cette approche permet de réduire l'impact de la sensibilité aux paramètres d'entrée.

### Particularité de l'immobilier : Location vs. Achat

Le choix immobilier (habiter en résidence principale ou louer) peut être simplifié dans le calcul de la manière suivante :

#### Assiette d'optimisation

Le particulier veut optimiser l'ensemble de la part de ses revenus dévolus à **habitation + épargne**.

On note **%S·S** cette part de son salaire.

**Cas locataire :**
- On note **%L** la part de %S·S utilisée pour se loger
- Donc : %S·S·%L = le loyer
- Base à optimiser : %S·S - %S·S·%L = %S·S·(1-%L)
- La base est donc réduite (impression de "jeter son argent par la fenêtre")

**Cas propriétaire :**
- Base à optimiser : %S·S (intégralité)

#### Procédure d'optimisation

Il faut procéder en **trois temps** :

**1. Augmenter les rendements des placements avec achat d'habitation propre**

Multiplier par le facteur **1/(1-%L)**

Raison : On compare, dans la théorie du portefeuille, les rendements au placement sans risque, mais ce dernier est sur l'assiette %S·S·(1-%L) car il est obligatoire de se loger ! On considère donc un sur-rendement du portefeuille du propriétaire en habitation propre.

**2. Calculer le portefeuille tangent dans chaque configuration**

- Avec achat pour habitation propre (δ = 1)
- Sans achat pour habitation propre (δ = 0, locataire)

**3. Comparer les pentes des portefeuilles tangents**

```
Pente(δ₀/₁) = (μ_tang(δ₀/₁) - r_ss_risk) / σ_tang(δ₀/₁)
```

Où :
- **μ_tang** : rendement espéré du portefeuille tangent
- **σ_tang** : volatilité du portefeuille tangent
- **r_ss_risk** : taux sans risque

**Le portefeuille avec la plus grande pente est le portefeuille optimum** (du moins pour un placement continu).

#### Vérification de réalisme

Il faut ensuite vérifier si les achats immobiliers équivalents à la répartition optimum sont réalistes, notamment pour l'achat d'habitation propre.

**Critère** : L'appartement correspondant doit répondre au critère de taille du particulier.

Sinon, il faut constituer un portefeuille avec l'appartement qu'il souhaiterait acheter pour habiter, lui adjoindre les autres placements selon l'optimisation, et vérifier que ce portefeuille reste acceptable.

### Particularité de l'investissement Pinel

L'avantage Pinel est considéré comme un **sur-loyer** :

```
RA_Pinel = RA_immo + Crédit_impôt(année)
```

Mais :
- Les frais d'acquisition sont augmentés du surcoût du neuf (~+10%)
- Le rendement locatif est abaissé (~-1% à confirmer)

---

## 8. Appétence au risque et horizon de placement

### Problématique

L'appétence au risque ne peut pas être demandée directement à l'utilisateur de manière fiable.

### Solutions possibles

**Solution 1 : Questionnaire**
- Quelques questions permettant de situer l'utilisateur
- Estimation qualitative de l'appétence au risque

**Solution 2 : Approche moyenne avec VaR (retenue)**
- Utilisation d'une appétence moyenne
- Présentation des résultats à l'utilisateur suivant **différentes VaR** (Value at Risk)
- L'utilisateur peut choisir selon son niveau de confort avec le risque

### Sensibilité

Nécessité de tester la sensibilité à ce paramètre avant de prendre une direction définitive.

---

## 9. Budget et dépenses prévisionnels de l'utilisateur

### Données de référence

Basé sur les données INSEE :
- **Source** : http://www.statistiques.developpement-durable.gouv.fr/lessentiel/ar/340/1207/tendances-caracteristiques-consommation-menages.html
- Données en % du (Revenu Net - Épargne)

### Pré-budget prévisionnel à t₀

Le pré-budget prévisionnel est basé sur les données INSEE en pourcentage du (Revenu Net - Épargne).

### Dépenses prévisionnelles supplémentaires

L'utilisateur peut ajouter des dépenses prévisionnelles supplémentaires :

| Catégorie | Dépendances |
|-----------|-------------|
| **Logement** | Si non intégré précédemment ; fonction du salaire et structure familiale |
| **Garde d'enfant** | Fonction de la déclaration de revenu |
| **Études** | Fonction de la déclaration de revenu |
| **Véhicule** | Changement ou premier achat, inclut prêt et décote ; fonction du salaire et argent disponible |
| **Santé prévu** | Ex : dents, chirurgie de confort... |
| **Budget vacances** | Fonction du salaire et argent disponible |
| **Suspension ou diminution de revenu** | Chômage ; probabilité basée sur chiffres INSEE et demande utilisateur |
| **Divers** | Cadeaux, dons, hobbies ; toutes dépenses autres que celles d'un foyer "moyen" ne générant pas de revenus ; fonction du salaire et argent disponible |
| **Profit d'une succession** | Montant et date estimée |

### Structure des dépenses

Toutes les dépenses sont construites de manière identique avec **5 variables** :

| Variable | Description |
|----------|-------------|
| **An_debut** | Année de début du projet |
| **M_debut** | Montant du premier versement (valeur d'aujourd'hui) |
| **M_vers** | Montant des versements annuels s'ils existent |
| **Duree** | Durée des versements en années |
| **M_sortie** | Montant (négatif) du revenu de sortie (ex : revente d'une voiture) |
| **An_decal** | Décalage possible du projet en année |

Ces données sont stockées dans une **matrice de dimension n × 5** (où n = nombre de projets).

---

## 10. Découpage du prévisionnel des cash-flows BaseLine

### Principe

Le projet est agrégé en une suite de **cash-flows** prenant en compte :
- L'épargne
- Net des frais d'un logement en location (à confirmer)

### Découpage en tranches de duration

Le flux de cash-flows est découpé en **tranches** (typiquement de 1 000 EUR) pour évaluer les placements de **durations identiques**.

### Schéma conceptuel

```
Temps →
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▲ Cash-flow
│
│     ┌───┐     ┌───┐           ┌───┐
│     │ 1 │     │ 2 │    ...    │ n │
│     └───┘     └───┘           └───┘
│      ↓         ↓               ↓
│   Duration  Duration        Duration
│      H₁        H₂              Hₙ
└────────────────────────────────────────→
```

Chaque tranche de cash-flow est associée à une duration spécifique (horizon de placement).

### Composition optimale par tranche

On peut ainsi définir, à partir de l'optimum de Markowitz, **la composition du placement optimum par tranche de duration** pour le flux de cash-flow objectif.

### Agrégation verticale

Les pourcentages de placements sont ensuite **réassemblés verticalement** pour obtenir la répartition des placements "BaseLine" pour l'ensemble de la projection.

**Résultat** : Un portefeuille qui tient compte des horizons de placement différents pour chaque flux de cash-flow.

---

## 11. ALM - Relation entre résultats et optionalité

### Principe de l'ALM (Asset Liability Management)

L'ALM permet de prendre en compte :
- **L'optionalité** : choix conditionnels selon les résultats
- **La non-proportionnalité de l'impôt** : barèmes progressifs
- **Le risque de chômage** : interruption temporaire de revenus

### Moteur ALM

Le moteur ALM rejoue pour **chaque période** l'évolution de :

1. **Placements** : évolution des actifs selon les scénarios
2. **Salaire** : évolution normale ou chômage éventuel
3. **Application des impôts** : selon les barèmes en vigueur
4. **Split capital liquide/non liquide** : disponibilité des fonds
5. **Calcul des dépenses** : selon le budget prévisionnel
6. **Application des objectifs** : sinon décalage dans le temps ou recours au crédit si possible

### Variables conditionnelles

Ces valeurs peuvent être basées sur :
- **Taux sans risque**
- **Inflation**
- **Variables macro** : à définir et modéliser
- **Taxes** : et leur évolution basée sur des variables macro

**Important** : Ces relations devront être confirmées par des études simples et conclusives. Leur impact peut être important et doit être évalué clairement dans le code.

### Évaluation par scénario

Chaque **scénario** (calcul vectorisé) est évalué au travers de :
- Placements optimisés dans la phase précédente
- Conditions économiques réelles (taxes, etc.)
- Optionalités (choix conditionnels)

### Résultats par scénario

Il en résulte les données suivantes par scénario :

| Donnée | Description |
|--------|-------------|
| **Cash flows moyens et VaR** | Gains et pertes cumulés |
| **Impôts payés** | Montants totaux et par type |
| **Intérêts de crédits** | Coûts du financement |
| **Probabilité de non-réalisation** | Probabilité de ne pas pouvoir réaliser les cash flows baseline |
| **Chronique des montants de succession** | Si décès |

### Montant de succession, retraite et assurance sociale

Ces éléments sont également modélisés dans le moteur ALM pour une vision complète du patrimoine sur l'ensemble de la vie.

---

## 12. GSE - Générateur de Scénarios Économiques

### Principe

Le GSE (Générateur de Scénarios Économiques) doit être **historique**.

### Approche retenue

Il a été choisi de partir d'un **GSE RN (Risque Neutre)** avec ajout d'une **prime de risque**.

**Avantage** : Cela évite de devoir choisir une fenêtre de temps pour le calibrage dont le choix serait la variable la plus sensible de l'étude.

### Modèles utilisés

#### Modèle de taux : Vasicek 1 facteur

- **Calibration** : à partir des prix de swaptions
- **Utilisation** : modélisation des taux d'intérêt

#### Actions : Black & Scholes

- **Drift** : égal au taux sans risque
- **Volatilité** : calibrée sur le prix des calls
- **Modélisation** : évolution des indices actions

#### Immobilier : Modèle propriétaire

- **Modèle propre** : développé spécifiquement
- **Benchmark** : comparé avec un modèle Black & Scholes

#### Prix de Marché du Risque (PMR)

- **Définition** : à partir des travaux de Caja
- **Calibration** : selon la même référence

#### Rendement de l'assurance vie

Modélisé comme :
```
Rendement_AV = Moyenne(OAT10 sur 4 ans) + 0,8%
```

**Note** : Modèle couramment utilisé par les organismes d'assurance.

#### OAT10 (Obligation Assimilable du Trésor 10 ans)

Modélisé à partir de :
- **Taux de base**
- **Ajout du risque de défaut** : par la méthode JLT
- **Calibration** : sur le prix des OAT10 du marché
- **Corrélation** : avec le PMR

**Avantage** : Permet de générer des évolutions de rendement pour différents types d'obligations (ratings et durations).

### Développement futur

Un futur développement devra permettre de **générer le GSE à partir d'un modèle de variables macroéconomiques**.

**Raison** : La durée de projection (30 ans ou plus) oblige à faire des hypothèses sur l'évolution des grandes masses macro-économiques.

---

## 13. Temps de calcul et optimisation

### Volume de calculs

Le calcul pour :
- Cash flows baseline
- Situation personnelle (salaire, structure familiale, succession, loyer, ville…)
- Appétence au risque

Va engendrer quelques **10 voire 100 000 calculs**.

### Optimisation du temps de calcul

Le temps de calcul sera optimisé par **calculs vectorisés** tant que possible.

### Limitation pour utilisation en temps réel

Il apparaît difficile voire impossible de pouvoir réaliser le calcul **en direct** lors de l'utilisation du site internet.

### Solutions envisagées

#### Solution 1 : Machine Learning / Deep Learning

**Approche** :
1. Utiliser les techniques du **machine learning** (type deep learning)
2. Synthétiser les résultats aux différents paramètres (trop nombreux pour être interpolés)
3. Étudier et développer dans un second temps après premiers résultats concluants

**Idée** :
- Laisser une grande puissance de calcul réaliser des runs pour des paramètres aléatoires (ou cadrillants)
- Utiliser ces runs pour **apprendre à un réseau de neurones** à répliquer les résultats

#### Solution 2 : Réseau de neurones inversé

**Approche** :
- Utiliser le réseau de neurones en mode **backward**
- Donner les résultats attendus (objectifs)
- Obtenir un set de données d'entrée permettant d'atteindre ces objectifs

**Note** : À confirmer (TBC - To Be Confirmed)

### Stratégie

Point à étudier et développer dans un second temps après les premiers résultats concluants.

---

## Conclusion

Le système Réoptimus propose une modélisation complète et rigoureuse de l'optimisation de l'épargne des particuliers, intégrant :

✅ **Modélisation réaliste** : Prise en compte des spécificités de l'investisseur particulier
✅ **Fiscalité détaillée** : Intégration complète des impôts, taxes et charges sociales
✅ **Optimisation scientifique** : Application de la théorie de Markowitz avec désensibilisation
✅ **Gestion dynamique** : ALM pour tenir compte des optionalités et aléas
✅ **Scénarios économiques** : GSE calibré sur les marchés financiers
✅ **Performance** : Solutions d'optimisation pour calculs en temps réel

Cette approche permet de fournir des recommandations d'investissement personnalisées, robustes et fiscalement optimisées pour les particuliers sur des horizons de placement longs (10-30 ans).

---

## Références

### Sources de données

- **INSEE** : Statistiques sur la consommation des ménages
  - http://www.statistiques.developpement-durable.gouv.fr/lessentiel/ar/340/1207/tendances-caracteristiques-consommation-menages.html

### Modèles financiers

- **Vasicek (1977)** : Modèle de taux d'intérêt à un facteur
- **Black & Scholes (1973)** : Modèle d'évaluation d'options et d'actifs
- **Markowitz (1952)** : Théorie moderne du portefeuille
- **Michaud (1998)** : Efficient Asset Management (méthode de bootstrap)
- **JLT (Jarrow, Lando, Turnbull)** : Modèle de risque de crédit

### Calibration

- **EIOPA** : European Insurance and Occupational Pensions Authority
  - Courbes de taux pour calibration
- **Caja** : Travaux sur le Prix de Marché du Risque

---

## Glossaire

| Terme | Définition |
|-------|------------|
| **ALM** | Asset Liability Management - Gestion Actif-Passif |
| **GSE** | Générateur de Scénarios Économiques |
| **MOCA** | MOnte CArlo - Simulation Monte Carlo |
| **VaR** | Value at Risk - Valeur à Risque |
| **CVaR** | Conditional Value at Risk - Valeur à Risque Conditionnelle |
| **PMR** | Prix de Marché du Risque |
| **PEA** | Plan d'Épargne en Actions |
| **OAT** | Obligation Assimilable du Trésor |
| **IR** | Impôt sur le Revenu |
| **CS** | Charges Sociales |
| **TF** | Taxe Foncière |
| **RN** | Risque Neutre |

---

## Notes d'implémentation dans FinancYou

Le système FinancYou implémente les principes Réoptimus à travers ses 5 modules :

1. **Module 1 (GSE)** : Générateur de Scénarios Économiques
   - Implémente les modèles Vasicek, Black-Scholes, Real Estate
   - Calibration EIOPA

2. **Module 2 (GSE+)** : Tax-Integrated Scenarios
   - Implémente la fiscalité multi-juridiction
   - Calculs des rendements nets après impôts et frais

3. **Module 3 (User Profile)** : Investment Time Series
   - Capture des dépenses prévisionnelles
   - Slicing par duration

4. **Module 4 (MOCA)** : Portfolio Optimizer
   - Optimisation de Markowitz
   - Simulations Monte Carlo
   - Calcul des VaR et CVaR

5. **Module 5 (Reporting)** : Visualization
   - Présentation des résultats
   - Analyse de sensibilité

Pour plus de détails sur l'implémentation, voir :
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MODULES_GUIDE.md](MODULES_GUIDE.md)
- [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)

---

**Document Version**: 1.0
**Date**: 2025-11-22
**Langue**: Français
**Base théorique**: Document original Réoptimus
