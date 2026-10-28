# Sorties du R d'origine sur les cas des tests, figées dans r_outputs.json.
#
# À relancer depuis la racine du dépôt quand on ajoute un cas :
#   Rscript tests/reference_r/generate_r_outputs.R
# Nécessite R (>= 4) et les paquets jsonlite et MASS. Les scripts R sont lus tels quels
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

# --- Reoptimus_striping.R : tranches (application) -------------------------
load_r(file.path(L, "ShinyR/BetaV1/Financyou/Data_Log/FCT_A/Reoptimus_striping.R"))
curves <- list(
  c(10000, 16000, 22000, 28000, 34000, 40000, 46000, 52000, 58000, 64000, 70000),
  c(10000, 16000, 22000, 28000, 14000, 20000, 26000, 32000, 38000, 44000, 50000),
  c(10000, 30000, 12000, 20000),
  c(20000, 26000, 32000, 8000, 14000, 20000, 26000),
  c(20000, 40000, 40000, 5000, 5000, 5000)
)
strip_out <- lapply(curves, function(a) {
  r <- tryCatch(stripping(5000, a), error = function(e) conditionMessage(e))
  if (is.character(r)) list(input = a, error = r) else list(input = a, output = unname(r))
})

# --- Assembl_investV3.R : répartition des tranches (application) ----------
load_r(file.path(L, "ShinyR/BetaV1/Financyou/Data_Log/FCT_A/Assembl_investV3.R"))
# Courbe des années 0 à 6, en tranches de 5 000 € écrites en dates R (année + 1).
assembl_capital <- c(10000, 15000, 15000, 20000, 20000, 10000, 0)
assembl_tr1 <- rbind(c(1, 6, 1), c(1, 6, 2), c(2, 5, 3), c(4, 5, 4))
assembl_weights <- list("2" = c(0.5, 0.5, 0), "4" = c(0.1, 0.6, 0.3), "6" = c(0.2, 0.3, 0.5))
horiz <- 7  # variable globale lue par Assembl_invest
assembl_soltot <- array(0, dim = c(3, horiz, horiz))
for (d in names(assembl_weights)) {
  assembl_soltot[, as.integer(d), ] <- assembl_weights[[d]]
}
assembl_gsepp <- array(1, dim = c(2, horiz, horiz, 3))  # rendements fictifs, non lus ici
assembl_res <- Assembl_invest(assembl_soltot, assembl_tr1, assembl_gsepp, assembl_capital)
# Une tranche présente une seule année (durée R de 1) fait échouer le R.
assembl_d1_error <- tryCatch({
  Assembl_invest(assembl_soltot, rbind(c(3, 3, 1)), assembl_gsepp, assembl_capital)
  "aucune erreur"
}, error = function(e) conditionMessage(e))
assembl_horiz <- horiz
horiz <- 20  # horizon des cas de projets, écrit plus bas

# --- Script_Bootstrap_V5_quick.R : rééchantillonnage de Michaud (MOCA) ---
suppressPackageStartupMessages(library(MASS))  # ginv
load_r(file.path(L, "MOCA/FCT/Script_Bootstrap_V5_quick.R"))
# Rendements annuels de 3 placements, 2 durées, 60 scénarios ; seule la date 1 est lue.
set.seed(20201113)
michaud_ns <- 60
michaud_returns <- array(0, dim = c(michaud_ns, 1, 2, 3))
for (d in 1:2) {
  michaud_returns[, 1, d, 1] <- 0.06 + 0.15 * rnorm(michaud_ns) / sqrt(d)
  michaud_returns[, 1, d, 2] <- 0.03 + 0.05 * rnorm(michaud_ns)
  michaud_returns[, 1, d, 3] <- 0.02 + 0.02 * rnorm(michaud_ns)
}
michaud_cases <- list(
  list(aversion = 8, nbboots = 4, constraints = c(0, 0, 0)),
  list(aversion = 1, nbboots = 3, constraints = c(0, 0, 0)),
  list(aversion = 8, nbboots = 4, constraints = c(0, 0.25, 0))
)
michaud_out <- lapply(michaud_cases, function(cs) {
  sol <- Boot_Michaud(michaud_returns, 0.5, cs$nbboots, cs$aversion, cs$constraints)
  c(cs, list(output = unname(sol)))
})

# --- fct_imp_IR.R : impôt par part, sur le barème du régime fr-2026 ---
load_r(file.path(L, "ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_imp_IR.R"))
ir_brackets <- fromJSON("investment_calculator/tax_regimes/fr-2026.json")$income_tax$brackets
tab_IR <- data.frame(Revenu.IR = ir_brackets$lower, Taux.IR = ir_brackets$rate)
ir_qf <- c(0, 5000, 11600, 11601, 20000, 29579, 35000, 60000, 84577, 90000,
           150000, 181917, 200000, 300000, 15000, 42000, 7000, 100000, 25000, 500000)
ir_out <- as.numeric(fct_flux_IR(ir_qf))  # lit la globale horiz = 20

# --- fct_crd_flux.R : crédits en cours ---
load_r(file.path(L, "ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_crd_flux.R"))
crd_cases <- list(
  list(horiz = 20, annuite = 12000, taux = 0.015, an_rest = 15),
  list(horiz = 10, annuite = 9000, taux = 0.04, an_rest = 18),
  list(horiz = 12, annuite = 6000, taux = 0, an_rest = 5)
)
crd_out <- lapply(crd_cases, function(cs) {
  res <- Flux_crd(cs$horiz, cs$annuite, cs$taux, cs$an_rest)
  c(cs, list(principal = as.numeric(res[[1]]), interest = as.numeric(res[[2]])))
})

# --- fct_recalcul_revenu.R et modif_chrono_flux_plc.R : bien loué à crédit ---
suppressPackageStartupMessages(library(dplyr))
load_r(file.path(L, "ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_recalcul_revenu.R"))
load_r(file.path(L, "ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/modif_chrono_flux_plc.R"))
rental_revenu <- lapply(c("RimmoLoc", "RimmoPinel", "Autre"), function(nom) {
  list(nom = nom, montant = 250000, output = fct_recalcul_revenu(nom, 250000, NULL))
})
# tab_chrono minimal : un salaire, deux parts, pas de loyer versé ni de projet.
horiz <- 20
rental_chrono <- function(salaire, parts) {
  rows <- rbind(
    c("life", "revenu", "salaire"), c("life", "hors_imp", "loyer"),
    c("life", "part_imp", "avec projets"), c("impots", "IR", "final"),
    c("life", "hors_imp", "depenses hors projets"),
    c("life", "hors_imp", "Epargne libre avec projets"), c("life", "credit sup", "0")
  )
  tc <- data.frame(type = rows[, 1], sous.type = rows[, 2], sous.type_2 = rows[, 3],
                   stringsAsFactors = FALSE)
  values <- matrix(0, nrow(rows), horiz)
  values[1, ] <- salaire
  values[3, ] <- parts
  cbind(tc, as.data.frame(values))
}
rental_case <- list(salaire = 60000, parts = 2, debut_optim = 4, annuite = 9000,
                    tau = 0.035, n = 15)
rental_case$montant <- rental_case$annuite * (1 - (1 + rental_case$tau)^-rental_case$n) /
  rental_case$tau + 20000
rental_case$revenu <- fct_recalcul_revenu("RimmoLoc", rental_case$montant, NULL)
rental_tc <- modif_chrono_flux_plc(
  rental_chrono(rental_case$salaire, rental_case$parts), rental_case$debut_optim,
  rental_case$revenu, Flux_crd(horiz, rental_case$annuite, rental_case$tau, rental_case$n),
  rep(0, horiz), "RimmoLoc"
)
rental_row <- function(st, st2) {
  as.numeric(rental_tc %>% filter(sous.type == st, sous.type_2 == st2) %>%
               select(-type, -sous.type, -sous.type_2))
}
rental_case$output <- list(
  revenu = rental_row("revenu", "ajout_RimmoLoc"),
  principal = rental_row("principal", "ajout_RimmoLoc"),
  interet = rental_row("interet", "ajout_RimmoLoc"),
  ir = rental_row("IR", "final")
)

out <- list(
  r_version = R.version.string,
  exp_proj_hist = list(horiz = horiz, cases = proj_out),
  exp_fin = list(horiz = horiz, sal_net = 18000, epar = 25000, output = as.numeric(cumul)),
  stripping = list(pas_e = 5000, cases = strip_out),
  assembl_invest = list(
    horiz = assembl_horiz, capital = assembl_capital, tr1 = unname(assembl_tr1),
    weights = assembl_weights, output = unname(assembl_res[[1]]),
    one_year_error = assembl_d1_error
  ),
  michaud = list(
    returns = michaud_returns[, 1, , ], cases = michaud_out
  ),
  imp_ir = list(qf = ir_qf, output = ir_out),
  crd_flux = crd_out,
  rental = list(revenu = rental_revenu, chrono = rental_case)
)
write_json(out, "tests/reference_r/r_outputs.json", digits = NA, auto_unbox = TRUE, pretty = TRUE)
