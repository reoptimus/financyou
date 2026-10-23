##########  library ################
library(shiny)
library(shinydashboard)
library(shinydashboardPlus)
library(shinyBS)
library(shinycssloaders)
library(shinyEffects)
library(shinyjs)
library(dashboardthemes)
library(V8)
library(shinyWidgets)
library(xlsx)
library(abind)
library(MASS)
library(plotly)
library(tidyr)
library(dplyr)
library(shinyalert)
library(data.table)
library(rdrop2)
library(htmltools)
library(viridis)
library(ggplot2)
library(hrbrthemes)
library(date)
library(DT)
library(glue)
library(ggrepel)
library(gridExtra)
library(devtools)
library(matrixStats)
library(moments)
library(stringr)
# library(rintrojs)
# library(waiter)
# install_github("nik01010/dashboardthemes")
# library(grid)
# install.packages("gridExtra",dependencies = TRUE)
# library(dash)
# library(dashCoreComponents)
# library(dashHtmlComponents)
setShadow <- shinyEffects::setShadow
##########  library fin ################

##########  token drop box ################
# rsconnect::showLogs()
# token <- drop_auth()
# saveRDS(token, "token.RDS")
# To use a stored token provide token location
# drop_auth(rdstoken = "token.RDS")
# drop_auth(new_user = TRUE, rdstoken = "token.rds")
token <- readRDS("token.RDS")
drop_acc(dtoken = token)
drop_auth(rdstoken = "token.RDS")
outputDir <- "FinancYou_data"
source(file="./Data_Log/FCT_A/FCT_dropbox.R")
# ecrase le fichier existant dans dataLog
loadData(outputDir,"BDD_List.Rda")
# saveData(outputDir,"BDD_List.Rda")
##########  token drop box fin ################

########## Meta donnees ##############
# chargement des donnÃÂ©es globales
reptravail<-""
chemin<-"./"
load(file=paste0(reptravail,chemin,"Data_Log/","BDD_List.Rda"))
load(file=paste0(reptravail,chemin,"Data_Log/","table_invest.Rda"))

# numerotation<-"20200120" # num GSE++
pas_E<-5000 # ici 1kEur, unite defini dans M_projets
Nbboots<-30
Aversion<-c(2)
seuil_filtre<-0.02 # seuil filtre pour la visualisation des poches de placements
# nom_GSE<-"Test_Hist_20200114.Rda"
pas_t<-0.5
horiz<-20 #doit correspondre Ã  GSE / GSE+ / GES++

# constante de l'app
lim_nb_proj<-5
lim_nb_plc<-10

limite_endt<-0.33 # limite du taux endettement accepte par les banques
########## Meta donnees fin ##############

########## fct visualisation ##############
source(file="./Data_Log/FCT_Global/fct_extraUI_dateMonths.R")
source(file="./Data_Log/FCT_Global/fct_uioutput_vous.R")
# graph des flux
source(file="./Data_Log/FCT_A/Visu_CF_V1.R")
source(file="./Data_Log/FCT_A/Visu_CF_cumul_V2.R")
source(file = "./Data_Log/FCT_A/Visu_CF_projets.R")
source(file = "./Data_Log/FCT_A/Visu_CF_V1_avec_proj.R")
source(file = "./Data_Log/FCT_A/Visu_CF_cumul_avec_proj.R")
source(file="Data_Log/FCT_A/Visu_CF_plc.R")
source(file = "./Data_Log/FCT_A/F_graph_optim_mat_result.R")
source(file = "./Data_Log/FCT_A/Visualisation_quantiles_V2.R")
source(file = "./Data_Log/FCT_A/Visualisation_liquide_endt.R")
source(file = "./Data_Log/FCT_A/fct_KPI.R")
########## fct visualisation fin ##############

########## chargement des tables Rda / excel ###########
# chgt fct pour generer les UI projets
# tab1<-read.xlsx("./Data_Log/Data/table_projets.xlsx", sheetIndex = 1, encoding="UTF-8")
# tab2<-read.xlsx("./Data_Log/Data/table_projets.xlsx", sheetIndex = 2, encoding="UTF-8" )
# names(tab1)<-c("id","fct","label","title")
# save(tab1,file="./Data_Log/Data/tab1.Rda")
# save(tab2,file="./Data_Log/Data/tab2.Rda")
load(file="./Data_Log/Data/tab1.Rda")
load(file="./Data_Log/Data/tab2.Rda")
#
# chgt fct pour generer les UI placements
# tab1_plc<-read.xlsx("./Data_Log/Data/table_plcs.xlsx", sheetIndex = 1, encoding="UTF-8")
# tab2_plc<-read.xlsx("./Data_Log/Data/table_plcs.xlsx", sheetIndex = 2, encoding="UTF-8")
# tab2_crd_imp<-read.xlsx("./Data_Log/Data/table_plcs.xlsx", sheetIndex = 3, encoding="UTF-8")
# names(tab1_plc)<-c("id","fct","label","title")
# save(tab1_plc,file="./Data_Log/Data/tab1_plc.Rda")
# save(tab2_plc,file="./Data_Log/Data/tab2_plc.Rda")
# save(tab2_crd_imp,file="./Data_Log/Data/tab2_crd_imp.Rda")
load(file="./Data_Log/Data/tab1_plc.Rda")
load(file="./Data_Log/Data/tab2_plc.Rda")
load(file="./Data_Log/Data/tab2_crd_imp.Rda")
#
# chgt de la table pour le calcul des taux remplacement retraites
# tab_retraite<-read.xlsx("./Data_Log/Data/Retraites_taux_rempla.xlsx", sheetIndex = 1, encoding="UTF-8")
# tab_coef_retraite<-read.xlsx("./Data_Log/Data/Retraites_coef_progress.xlsx", sheetIndex = 1, encoding="UTF-8")
# save(tab_retraite,file="./Data_Log/Data/tab_retraite.Rda")
# save(tab_coef_retraite,file="./Data_Log/Data/tab_coef_retraite.Rda")
load(file="./Data_Log/Data/tab_retraite.Rda")
load(file="./Data_Log/Data/tab_coef_retraite.Rda")
# tab_IR<-read.table(file="./Data_Log/Data/Tranche_marginale_IR.csv",header = TRUE, sep=";")
# save(tab_IR,file="./Data_Log/Data/tab_IR.Rda")
load(file="./Data_Log/Data/tab_IR.Rda")
# Tab_conso_foyer<-read.xlsx("./Data_Log/Data/Part_conso_foyer.xlsx", sheetIndex = 1, encoding="UTF-8")
# save(Tab_conso_foyer,file="./Data_Log/Data/Part_conso_foyer.Rda")
load(file="./Data_Log/Data/Part_conso_foyer.Rda")
Part_conso_foyer<-as.numeric(as.character(Tab_conso_foyer$Oxford))

# load(file=paste0(reptravail,chemin,"Data_Log/","GSE+.Rda"))
# variables: cube_placement et list_actifs et GSE++
numero_alpha<-"_13112020"
numerotation_GSE<-"20200820"
load(file=paste0("Data_Log/Data/Tab_alpha_approx",numero_alpha,".Rda"))
load(file=paste0("Data_Log/Data/List_alpha_approx",numero_alpha,".Rda"))
load(file=paste0("Data_Log/Data/List_plc",numero_alpha,".Rda")) # list_placements_compl
List_Av<- c(0.5, 5,50) # doit correspondre aux alpha simplifications
# Tr_imp<- tab_IR[,2]
# for (i in 1:length(Tr_imp)){
# load(paste0(reptravail,chemin,"Data_Log/GSE++/","GSE++_",numerotation_GSE,"_",as.character(Tr_imp[i]),".Rda"))
# # dim(GSE_plac_taxes_cuml)
# }

########### fct server #############
source(file="./Data_Log/FCT_Global/Exp_proj_hist.R")
source(file="./Data_Log/FCT_Global/fct_chrono_flux.R")
source(file="./Data_Log/FCT_Global/fct_crd_flux.R")
source(file="./Data_Log/FCT_Global/fct_crd_imp_flux.R")
source(file="./Data_Log/FCT_Global/fct_imp_IR.R")
source(file="./Data_Log/FCT_Global/Lancement_MOCA_A.R")
source(file="./Data_Log/FCT_Global/fct_MOCAdre.R")
source(file="Data_Log/FCT_A/Assembl_investV3.R")
source(file="Data_Log/FCT_A/Reoptimus_striping.R")
source(file="./Data_Log/FCT_Global/modif_chrono_flux_plc.R")
source(file="./Data_Log/FCT_Global/modif_tabl_plac.R")
source(file="./Data_Log/FCT_Global/fct_contraintes_eur.R")
source(file="Data_Log/FCT_Global/CF_cumul_avec_proj.R")
source(file="Data_Log/FCT_Global/fct_discret_optim.R")
source(file="Data_Log/FCT_Global/fct_recalcul_revenu.R")
source(file="Data_Log/FCT_Global/fct_prod_soltot.R")
source(file="Data_Log/FCT_Global/fct_optim_interm.R")
########### fct server fin #############

########### fct global a reunir ds un code ########

##### Varinput_i : generation autom des UI
varinput_i <- function(i, label_ext="" ) {
  
  idi<-as.character(tab1[i,1])
  #ns <- NS(idi)
  fcti<-as.character(tab1[i,2])
  
  labeli<-tab1[i,3] # tab1[,3]
  labeli<-paste("list(",labeli,")")
  labeli<-paste0("labeli<-", labeli)
  eval(parse(text=labeli))
  
  status_list=c("primary", "success","info", "warning", "danger")
  tagList(
    box(title=as.character(label_ext) ,do.call(fcti,c(idi, labeli )), #ns(idi)
        width=6,status=status_list[sample(1:5,1)],#background="teal",
        solidHeader = FALSE, collapsible=FALSE,# collapsed=FALSE,
        closable=FALSE)
  )
}
##### Varinput_i_plc
varinput_i_plc <- function(i, label_ext="" ) {
  
  idi<-as.character(tab1_plc[i,1])
  #ns <- NS(idi)
  fcti<-as.character(tab1_plc[i,2])
  
  labeli<-tab1_plc[i,3]
  labeli<-paste("list(",labeli,")")
  labeli<-paste0("labeli<-", labeli)
  eval(parse(text=labeli))
  
  status_list=c("primary", "success","info", "warning", "danger")
  tagList(
    box(title=as.character(label_ext) ,do.call(fcti,c(idi, labeli )), #ns(idi)
        width=6,status=status_list[sample(1:5,1)],#background="teal",
        solidHeader = FALSE, collapsible=FALSE,# collapsed=FALSE,
        closable=FALSE)
  )
}

# definition de la fonction is.empty
is.integer0 <- function(x)
{is.integer(x) && length(x) == 0L}

# fonction de  MEF des DataTable
MEF_DT<- function(df){
  datatable(df,
            class = "display", #'cell-border compact'
            filter = "none",
            selection = "none", escape=F , editable = FALSE,
            rownames=F , 
            options = list( dom='t',
                            columnDefs = list(list(className = 'dt-center', targets = "_all")))
  )
}

# fonction d'enregistrement de hist
enr_hist<-function (pseudo,passwd,hist_) {
test_pass<-paste0(BDD_List$pseudo,BDD_List$pass)==paste0(pseudo,passwd)
if (sum(test_pass)==0) { # user pas retrouve
  ligne <- 2
} else { if (sum(test_pass)==1) {#trouve
  ligne <- which(test_pass)
} else { #pb plusieur fois meme user
  ligne=2
}
}
user_projets<-hist_
var_base<-paste0("F_",BDD_List[ligne,3])
save(user_projets,file=paste0(reptravail,chemin,"Data_Log/",var_base,".Rda"))
saveData(outputDir,paste0(var_base,".Rda"))
}
# pseudo<-"test"
# passwd<-"passtest"
# enr_hist(pseudo,passwd,hist_)

decoup_text<-function(chaine,nb_lim) {
  # chaine<-"Sera-t-il constant ou Ã©volura-t-il comme vos revenus?"
  # nb_lim<-12
  nb_car<-nchar(chaine)
  taglist<-tagList()
  lettre_fin<-0
  indic<-0
  while(indic==0) {
    lettre_debut<-lettre_fin+1
    lettre_fin<-lettre_debut+nb_lim
    if (lettre_fin>=nb_car) {indic<-1} else {indic<-0
    if (lettre_fin!=" "&lettre_fin!="."&lettre_fin!="?") {
      a<-gregexpr(" ",substr(chaine,start = lettre_debut,stop=lettre_fin))[[1]]
      lettre_fin<-max(0,a[length(a)])+lettre_debut-1
    } else {
    }
    }
    taglist<-tagList(taglist,str_sub(chaine, lettre_debut, min(lettre_fin,nb_car)  ),br()   )
  }
  return(taglist)
}  
########### fct global a reunir ds un code fin ########

############ divers : theme / JS code / html ##########
source(file="./Data_Log/Custom_theme.R")
logo_blue_gradient <- shinyDashboardLogoDIY(
  boldText = "Financ"
  ,mainText = ""
  ,textSize = 18
  ,badgeText = "You"
  ,badgeTextColor = "rgb(0,0,150)" #rgba(44,222,235,1)"
  ,badgeTextSize = 3
  ,badgeBackColor = "rgb(0,112,189)"
  ,badgeBorderRadius = 3
)
# added fct in JScode
jscode <- "
shinyjs.toggleBox = function(boxid) {
$('#' + boxid).closest('.box').find('[data-widget=collapse]').click();
};
shinyjs.collapseBox = function(boxid) {
$('#' + boxid).collapse('hide')};
shinyjs.expandBox = $function(boxid) {
$('#' + boxid).collapse('show')};
"

############ divers : theme / JS code / html fin ##########

############# boxPlus info ############################
tab_info_box<-read.xlsx("./Data_Log/Data/table_info_boxplus.xlsx", sheetIndex = 1, encoding="UTF-8")
boxPlusInfo<-function (idi=id,taglisti=taglist, widthi ,content_numi) { 
  # content_numi<-2
  ligne<-tab_info_box[which(tab_info_box$num==content_numi),]
  text1<-decoup_text(as.character(ligne$text1),ligne$long1)
  text2<-decoup_text(as.character(ligne$text2),ligne$long1)
  sidebar_contenti<-tagList(span(text1, style=ligne$type1),span(text2, style=ligne$type2))
  
  statusi<-ligne$status
  solidHeaderi<-ligne$solidHeader
  collapsiblei<-ligne$collapsible
  if (as.logical(solidHeaderi)==TRUE) {
    titlei<-span(ligne$title, style="color:white; font-weight:bold ;  text-align: justify" )
  } else {titlei<-span(ligne$title, style="color:black; font-weight:bold ;  text-align: justify" )
  }
  
  box<-box(id=idi,
               width = widthi,
               title = titlei, 
               closable = FALSE, 
               status = statusi, 
               solidHeader = as.logical(solidHeaderi), 
               collapsible = as.logical(collapsiblei),
               enable_sidebar = TRUE,
               sidebar_width = as.numeric(as.character(ligne$ratio)),
               sidebar_start_open = FALSE,
               sidebar_content = sidebar_contenti,
               taglisti )
  return(box)
}
