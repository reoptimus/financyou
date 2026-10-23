########################
#
# process de creation d'un package / shiny avec Test
#
# package: usethis , golem , testthat
#
# 22/11/2020
#
########################

install.packages('installr')
remotes::install_github('r-lib/pkgbuild')
library(installr)
install.Rtools(choose_version = TRUE, check = FALSE, GUI = TRUE,page_with_download_url = "https://cran.r-project.org/bin/windows/Rtools/")

install.packages(c("devtools", "usethis", "roxygen2"))
library(usethis)
library(devtools)
library(roxygen2)
install.packages("testthat")
library(testthat)

# verifier le nom du package
AVAILABLE::AVAILABLE("MONPACKAGE")
# Create a new package -------------------------------------------------
path <- file.path( "./financyour")
create_package(path)

# Modify the description ----------------------------------------------
use_mit_license("SebGallet")
#> ✓ Setting License field in DESCRIPTION to 'MIT + file LICENSE'
#> ✓ Writing 'LICENSE'
#> ✓ Writing 'LICENSE.md'
#> ✓ Adding '^LICENSE\\.md$' to '.Rbuildignore'

use_test("tests")
#> ✓ Adding 'testthat' to Suggests field in DESCRIPTION
#> ✓ Setting Config/testthat/edition field in DESCRIPTION to '3'
#> ✓ Creating 'tests/testthat/'
#> ✓ Writing 'tests/testthat.R'
#> ✓ Writing 'tests/testthat/test-my-test.R'
#> ● Edit 'tests/testthat/test-my-test.R'

# ajoute des donnees
use_data(x, y)

# creer une vignette explicative du package
usethis::use_vignette("How_use_Financyour")
# ajout d'une dependence
devtools::use_package("stats")
# creation de la doc
devtools::document()
# installer le package
devtools::install()

system.file("global.R",package="financyour")

.libPaths()
