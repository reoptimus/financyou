# R_Financyou : le code R d'origine, complet

Archive `R_Financyou.zip` retrouvée et transmise par seb le 2026-10-23. Elle
contient tout le code R de FinancYou (2017 à décembre 2020) : le GSE, le GSE+,
le GSE++, le moteur MOCA et l'application Shiny. L'arborescence d'origine est
conservée telle quelle, parce que les scripts s'appellent entre eux par
chemin relatif à `reptravail` (par exemple `"/MOCA/OUT/Strip_invest.Rda"`).

Comme le reste de `legacy/`, ce répertoire est en **lecture seule** : c'est la
référence contre laquelle le portage Python est vérifié. L'inventaire, la
couverture Python et l'ordre de portage sont dans
[`docs/portage-r/inventaire-code-r.md`](../../docs/portage-r/inventaire-code-r.md).

## Rapport avec `legacy/R_scripts/`

`legacy/R_scripts/` est une copie à plat d'une partie de cette archive. Ses 58
scripts s'y retrouvent tous, octet pour octet, à un des emplacements
d'origine. Quand un même nom existe en plusieurs copies dans l'archive, les
copies peuvent différer : voir l'inventaire.

## Ce qui n'a pas été versionné, et pourquoi

Rien n'a été modifié dans les scripts, sauf les deux retraits d'identifiants
signalés plus bas. Ont été laissés hors du dépôt :

| Exclu | Raison |
|---|---|
| `ShinyR/BetaV1/Financyou/token.RDS` | Jeton d'accès Dropbox de l'application. Secret. |
| `ShinyR/BetaV1/Financyou/rsconnect/` | Métadonnées de déploiement shinyapps.io. |
| `ShinyR/BetaV1/Financyou/Data_Log/F_*.Rda`, `BDD_List.Rda`, `MOCA/IN/BDD.Rda`, `MOCA/OUT/Mat_result_client1.Rda` | Comptes et dossiers des utilisateurs de l'application (pseudos, mots de passe, profils). |
| `.Rhistory`, `.RData`, `.Rproj.user/` | Historiques et espaces de travail de session R. |
| `WIX/`, images de `www/` | Visuels du site, dont des photos sous licence iStock. |
| `*.pdf`, `*.html`, `*.tex`, `figure-html/`, `*.docx` | Sorties de rapports, une publication Banque de France, deux notes de 2017 (analyse juridique et validation du GSE). |
| `*.xlsm`, `financyour_0.0.0.9000.tar.gz` | Classeurs à macros et paquet R compilé. |
| Fichiers de plus de 1 Mo | Sorties volumineuses (`GSE+.Rda`, `Test_Hist_20200114.Rda`, `ESG-martingal.Rda`, `Tab_alpha_approx_*.Rda`), données Bloomberg et courbe EIOPA d'avril 2018. `Tr-action.Rda`, `Tr-immo.Rda` et `Epsilon.Rda` sont déjà dans `legacy/R_data/`, identiques. |

L'archive complète reste dans les fichiers du projet (`R_Financyou.zip`).

## Identifiants retirés

- `ShinyR/Script_load.R` contenait le jeton et le secret du compte
  shinyapps.io. Ils sont remplacés par `Sys.getenv('SHINYAPPS_TOKEN')` et
  `Sys.getenv('SHINYAPPS_SECRET')`.
- `ShinyR/BetaV1/Financyou/server.R` et
  `Data_Log/FCT_Global/fct_uioutput_vous.R` contenaient en commentaire le mot
  de passe d'un compte de l'application, remplacé par `"[retire]"`.
