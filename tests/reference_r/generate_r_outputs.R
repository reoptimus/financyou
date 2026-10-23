# Sorties du R d'origine sur les cas des tests, figées dans r_outputs.json.
#
# À relancer depuis la racine du dépôt quand on ajoute un cas :
#   Rscript tests/reference_r/generate_r_outputs.R
# Nécessite R (>= 4) et le paquet jsonlite. Les scripts R sont lus tels quels
# dans legacy/, après translittération en ASCII de leurs commentaires
# (leur encodage est mélangé et R refuse de les lire sinon).

suppressPackageStartupMessages(library(jsonlite))
pdf(NULL)  # Exp_finance_hist.R trace des graphiques
L <- "legacy/R_Financyou"
load_r <- function(path) {
  src <- iconv(readLines(path, warn = FALSE), from = "UTF-8", to = "ASCII//TRANSLIT", sub = "")
  eval(parse(text = src), envir = globalenv())
}

# --- Exp_proj_hist.R : flux d'un projet (application) ---------------------
load_r(file.path(L, "ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/Exp_proj_hist.R"))
exp_proj_hist <- Exp_fin
# start, mdebut, mvers, duree, msortie
projects <- list(
  c(3, 5000, 2000, 4, -3000),
  c(0, 1000, 6000, 5, 0),
  c(7, 15000, 0, 0, 0),
  c(2, 40000, 9000, 15, -120000),
  c(19, 1000, 500, 1, -200),
  c(20, 2500, 0, 0, 0),
  c(15, 50000, 10000, 10, -300000),
  c(-2, 8000, 3000, 5, 0),
  c(4, 1000, 0, 0, -500)
)
horiz <- 20
proj_out <- lapply(projects, function(p) {
  debut <- Sys.Date() + 365 * p[1]  # floor(jours / 365) redonne p[1]
  list(input = p, output = as.numeric(exp_proj_hist(horiz, debut, p[2], p[3], p[4], p[5], 0)))
})

# --- Exp_finance_hist.R : somme cumulée (MOCA) -----------------------------
load_r(file.path(L, "MOCA/FCT/Exp_finance_hist.R"))
# Exp_fin de MOCA ignore les projets commençant à 0 et écrase le dernier
# versement par la sortie : on lui passe une ligne neutre et l'on ajoute
# les flux des projets ci-dessus pour isoler la somme cumulée.
rows <- do.call(rbind, lapply(proj_out[1:6], function(p) p$output))
M <- data.frame(Nom = "neutre", Debut = 1, Versement = 0, Mensualite = 0, Duree = 0, Revente = 0)
base <- Exp_fin(M, horiz, 18000, 25000)
cumul <- base - cumsum(colSums(rows))

out <- list(
  r_version = R.version.string,
  exp_proj_hist = list(horiz = horiz, cases = proj_out),
  exp_fin = list(horiz = horiz, sal_net = 18000, epar = 25000, output = as.numeric(cumul))
)
write_json(out, "tests/reference_r/r_outputs.json", digits = NA, auto_unbox = TRUE, pretty = TRUE)
