# Interface des prototypes R : écrans, questions, écarts avec l'application

Date : 2026-11-16. Source : trois archives de prototypes Shiny fournies par seb
(dossier projet `377f0244….tar` et deux archives jointes). Aucune n'est versée
dans le dépôt : elles contiennent des comptes utilisateurs (`F_*.Rda`,
`BDD*.Rda`), un jeton Dropbox (`token.RDS`) et, pour l'une, un jeton OAuth
(`.httr-oauth`). **Ces jetons sont à révoquer s'ils sont encore valides.**

## 1. Les trois versions

| Version | Archive | Écrans (menu) | Remarques |
|---|---|---|---|
| A, la plus ancienne | `357a5e32…` | Vos projets, Vous, Vos anticipations, Vos projections, Et si…, Optimisez | Saisie par tableaux (`rHandsontable`). Anticipations et projections « en construction ». Onglet Optimisez : flux, diversification, scénarios. |
| B | `427f2fd5…` | Connexion, Vous, Vos projets, Vos anticipations, Vos projections, Et si ? | Questionnaire par sliders, en panneaux repliables. Seule version où « Vos anticipations » est rempli (tendance économique, acceptation du risque). |
| C, la plus aboutie | `377f0244…` | Connexion, Vous, Votre patrimoine, Vos projets, Vos projections, À venir | Variante de `legacy/R_Financyou/ShinyR/BetaV1/Financyou` (déjà versée par la PR #49), écrite pour une version plus ancienne de `shinydashboardPlus`. Chaque boîte porte un texte d'aide lu dans `table_info_boxplus.xlsx`. |

Le parcours s'est stabilisé ainsi dans la version C : **Vous → Votre
patrimoine → Vos projets → Vos projections**. Chaque écran est coupé en deux :
la saisie à gauche (accordéons), un graphique qui se met à jour à droite.

## 2. Les questions posées, écran par écran

### Vous (versions B et C)

| Bloc | Question | Réponse attendue | Dans l'application |
|---|---|---|---|
| Ressources | Adultes dans le foyer fiscal ? | 1 ou 2 | Oui (case « couple » du profil, reprise par le budget) |
| | Revenu net imposable annuel, de chaque adulte | k€ | Oui (budget), et en double dans le profil |
| | Épargne annuelle, hors remboursement de crédits | € | Oui (épargne mensuelle du profil) |
| | Évolution attendue des revenus, hors inflation | % | Oui (budget, par adulte) |
| | Votre niveau de vie est-il stable ou suit-il vos revenus ? | stable / suit les revenus | Oui (case « les dépenses suivent les revenus ») |
| Foyer fiscal | Âge de chaque enfant à charge | 0 à 25 ans, jusqu'à 6 enfants | Partiel : nombre d'années à charge, saisi en texte libre |
| | Pension alimentaire reçue / versée, et son montant | € | **Non** : lacune déclarée du budget, son traitement fiscal manque au régime |
| Logement | Êtes-vous propriétaire de votre logement ? | oui / non | **Non** : seul le loyer annuel est demandé |
| | Valeur du bien, prix net vendeur | k€ | **Non** : la résidence principale n'entre pas dans le patrimoine |
| | Avez-vous fini de le payer ? Sinon : durée totale, durée restante, taux, mensualité | | Partiel : un crédit générique sur la page Budget |
| | Locataire : loyer mensuel charges comprises | € | Oui, mais annuel |
| Situation professionnelle | Catégorie socio-professionnelle, de chaque adulte | libéral, salarié, fonctionnaire… | Non, par choix (2026-10-24) : le taux de remplacement est saisi |
| | Nombre d'années avant la retraite à taux plein | ans | Oui (budget) |

### Votre patrimoine (version C)

Un placement se choisit par type puis par produit ; les champs dépendent du produit.

| Produit | Champs demandés | Dans l'application |
|---|---|---|
| Actions PEA, ETF PEA | nom, montant, zone géographique, secteur | Montant, versements, ancienneté ; ni zone ni secteur |
| OPCVM monétaire, compte courant, Livret A | nom, montant | Oui |
| Assurance vie | nom, montant, part d'unités de compte | Partiel : le fonds en euros et les UC sont deux placements du catalogue |
| Immobilier locatif, Pinel en cours, résidence secondaire | valeur, mensualité, taux, années restantes, années totales, loyer | Partiel : la page Investissement locatif décrit un achat, pas un bien déjà détenu |

Le graphique associé montre la répartition du patrimoine en brut (valeur de
revente) et en net (après capital restant dû et impôt de plus-value).

### Vos projets (versions A, B, C)

Le projet se choisit dans un catalogue par famille, chaque modèle posant ses
propres questions (`table_projets.xlsx`, feuille `tab2`) :

| Famille | Modèle | Questions | Dans l'application |
|---|---|---|---|
| général | dépense instantanée ; dépense importante (voyage) | date, montant | Formulaire générique seulement |
| | dépense importante avec frais d'entretien (bateau) | date, montant, frais annuels | idem |
| | dépense via crédit | date, montant, durée, taux | idem |
| | investissement avec gains annuels | période, mise, recette annuelle | idem |
| famille | études supérieures | période, montant annuel | idem |
| | agrandir la famille | date | Oui (page Budget, « naissances ou adoptions à venir ») : une part fiscale de plus et un coût annuel saisi par l'utilisateur, à la place des unités de consommation non sourcées |
| équipement | chauffage basse consommation, travaux BBC ou non, panneaux solaires | date, coût, économie annuelle, durée de vie | Formulaire générique seulement ; crédits d'impôt non portés |
| travail, loisir | temps partiel, arrêt d'un conjoint, congé sans solde | période, part travaillée, quel conjoint | Oui (page Projets, section « Temps partiel ou congé ») : réduit le salaire dans le budget ; pension et allocations inchangées, lacune déclarée |
| immo | investissement locatif, Pinel, résidence secondaire | date, prix, loyer, taux, durée, apport | Page Investissement locatif ; Pinel non porté |

Deux graphiques accompagnent la saisie : la chronologie des flux des projets et
la répartition du budget année par année.

### Vos anticipations (version B seulement)

- « Quelle est selon vous la tendance économique pour les 20 prochaines
  années ? » : croissance espérée (2 %), faible (1 %), stagnation (0 %).
- « Quel niveau de risque êtes-vous prêt à prendre pour augmenter vos
  rendements ? » : oui / un peu / le minimum.

La première question contredit la règle du 2026-10-29 : la dynamique des
marchés vient des scénarios du GSE, jamais d'un taux saisi. Elle n'est pas à
reprendre. La seconde correspond à l'aversion au risque λ du menu latéral ;
la traduire en trois valeurs de λ demanderait des valeurs que rien ne fonde
aujourd'hui.

### Vos projections (version C)

Deux colonnes, hors projets et avec projets, chacune avec :

1. le cumul de l'épargne directe ;
2. le capital par niveau de probabilité (« 10 % de chances d'être en dessous ») ;
3. deux limites à ne pas franchir : capital net et épargne de précaution.

Au centre, six indicateurs comparés hors projets / avec projets : total des
revenus, des dépenses, des impôts, taux d'endettement maximal, épargne de
précaution minimale.

L'application affiche le patrimoine net médian, une cascade des coûts, la
frontière efficiente, le budget et le plan par tranches. Elle n'a ni bandes de
probabilité sur le patrimoine, ni comparaison hors projets / avec projets.

### Autres

- **Connexion** : pseudo et mot de passe, sans e-mail, pour retrouver sa
  saisie. L'application ne garde rien d'une session à l'autre.
- **Et si…** : rejouer 2008, le choc pétrolier de 1978, la baisse de
  l'immobilier des années 1990. Jamais construit.

## 3. Ce qu'il est proposé de reprendre

Par ordre de valeur pour l'utilisateur, une PR par ligne :

1. **Projets guidés par modèle** (cette PR) : les modèles du R dont le calcul
   ne demande que les montants saisis par l'utilisateur. Chacun se traduit
   dans le format projet existant (début, versement initial, versement annuel,
   durée, revente) ; aucune valeur n'est ajoutée.
2. **Logement** : propriétaire ou locataire, crédit de la résidence
   principale, valeur du bien dans le patrimoine. La valeur nette (valeur
   selon l'indice immobilier du GSE, moins capital restant dû) s'affiche à
   part ; elle n'entre pas dans le patrimoine financier optimisé.
3. **Âges des enfants** à la place des années à charge. L'âge de fin de
   charge est saisi par l'utilisateur : il dépend du foyer (études,
   rattachement au foyer fiscal), aucune valeur n'est supposée.
4. **Projections avec et sans projets**, avec les bandes 5-95 % du patrimoine
   et les indicateurs du R qui existent déjà dans le budget (impôts, taux
   d'endettement, épargne libre minimale).
5. **Sauvegarde de la saisie** dans un fichier à télécharger puis recharger,
   sans compte ni serveur.
6. **Textes d'aide** de `table_info_boxplus.xlsx`, revus, sur chaque champ.
   Le renvoi au barème d'Oxford (OCDE) du texte 15 n'est pas repris : les
   unités de consommation ne sont pas portées.

Restent hors de portée tant qu'une donnée validée manque : pension
alimentaire, Pinel et crédits d'impôt travaux, « Et si… » (scénarios historiques à calibrer).

## 4. Écarts volontaires avec le R, pour les modèles de projets

- **Dépense via crédit.** Le R calcule la mensualité par
  `(-b*d*0.01)/(1-(1+d)^c)`, où le taux est pris tantôt en pour cent, tantôt
  en fraction. Le portage applique l'annuité constante
  `C × t / (1 − (1 + t)^−n)`, en annuités annuelles comme le reste du modèle.
- **Économie annuelle des travaux.** Le R l'ajoute en revenu ; ici elle
  devient un versement annuel négatif du projet, pendant la durée de vie de
  l'installation, ce qui revient au même dans la courbe de capital.
