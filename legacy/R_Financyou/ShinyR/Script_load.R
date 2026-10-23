#####################
#
# Script pour loader l'app sur Shinyapp.io
#
#####################
library(shiny)

if(!require("devtools"))
  install.packages("devtools")
devtools::install_github("rstudio/rsconnect")

# copier le token et lancer (identifiants retires du depot : variables d'environnement)
rsconnect::setAccountInfo(name='reoptimus',
                          token=Sys.getenv('SHINYAPPS_TOKEN'),
                          secret=Sys.getenv('SHINYAPPS_SECRET'))

# pointer l'adresse de l'app
adresse<-"E:/R_Financyou/ShinyR/BetaV0/V0.0/Test_shiny"
rsconnect::deployApp(adresse)

rsconnect::appDependencies()

runApp()