#######################
#
# Lancement MOCA : Calcul global a partir du GSE
# 
#
# modifie le 28/01/2020
# par S?bastien Gallet
#########################
library(xlsx)
library(abind)
library(MASS)
library(plotly)
library(tidyr)
library(dplyr)
library(shiny)
library(shinydashboard)
########################
# variables hat: Meta donnees
reptravail<-"D:" # "E:"
reptravail<-paste0(reptravail,"/R_Financyou")

numerotation<-"20200120"
table_placement<-"Table_placements"
pas_E<-5000 # ici 1kEur, unite defini dans M_projets
Nbboots<-50
Aversion<-c(5,50,200,500,1000)
nom_solution<-"soltot" #solution marko pour le cas de calcul
nom_client<-"client1" # nom de sauvegarde de la solution
seuil_filtre<-0.02 # seuil filtre pour la visualisation des poches de placements
# table_invest<-read.xlsx(paste0(reptravail,"/GSE+/R1 CUBE++/R1 IN/","Table_placements",".xlsx"),sheetIndex = 1)

nom_GSE<-"Test_Hist_20200114.Rda"
pas_t<-0.5
horiz=30 # horizon de placements

file<-paste0(reptravail,"/MOCA/IN/BDD.Rda")
load(file)
########################
#donnee utilisateur
nom_user<-"test"
passwd<-"passtest"

nb_select<-which((paste0(BDD$pseudo,BDD$pass)==paste0(nom_user,passwd))==TRUE)
if (length(nb_select)!=1) {
  print("plusieurs fois le meme pseudo")
} else {
  print("utilisateur trouve")
}


Net_imposable<-as.data.frame(BDD[nb_select,]$revenu)$Net_imposable
taux_eparg<-as.data.frame(BDD[nb_select,]$revenu)$taux_eparg
Loyer<-as.data.frame(BDD[nb_select,]$fiche)$Loyer
tabl_plac<-as.data.frame(BDD[nb_select,]$plc)
 sum_annuite<-sum(tabl_plac$Annuite)
# correction de valeurt0 pour les credits en cours
tabl_plac$Valeur_t0_Rest_crd<-tabl_plac$Annuite*(1-(1+tabl_plac$Taux)^(-tabl_plac$An_rest))/tabl_plac$Taux
tabl_plac$Valeur_t0_Rest_crd[which(tabl_plac$Annuite!=0)]<-tabl_plac$Valeur_t0[which(tabl_plac$Annuite!=0)]-tabl_plac$Valeur_t0_Rest_crd[which(tabl_plac$Annuite!=0)]
tabl_plac$Valeur_t0_Rest_crd[which(is.na(tabl_plac$Valeur_t0_Rest_crd))]<-tabl_plac$Valeur_t0[which(is.na(tabl_plac$Valeur_t0_Rest_crd))]

salNet<-as.integer((Net_imposable-Loyer)*taux_eparg+sum_annuite) #salaire netnet annuel (hors toutes depenses) + le remboursements credits
epar<-sum(tabl_plac$Valeur_t0_Rest_crd) #epargne reelle a t0

#########################
# Mise en forme du profil financier de l'investisseur

M_projets<-as.data.frame(BDD[nb_select,]$projets)
#########################

#########################
# calcul du GSE+ : formation des produitsde placements accessibles par un particulier
source(file=paste0(reptravail,"/GSE+/R2 CUBE+/R2 FCT/Produits_placements.R"))
produits_placements(reptravail,nom_GSE,pas_t)
#Net_imposable<-50000 # interne au calcul GSE++ 
# n duree de l'emprunt interne au calcul!!!
cubecumul<-"GSE+.Rda" #Test_ReO.V1.Rda"
titre<-paste0("cas ",numerotation,":invest ",epar/1000)

source(file=paste0(reptravail,"/GSE+/R1 CUBE++/R1 FCT/Earn_Aft_Int_TaxesV2.R"))
Earn_Aft_Int_Taxes(cubecumul,pas_t,horiz,reptravail,table_placement,epar,Net_imposable,numerotation)

#########################
# calcul du GSE++ : modification des rendements suites aux impots et taxes et credit 
#########################
# definition des GSE++ pour les differentes ?tape de calcul utilisateur
# les placements investissable ne sont pas les m?mes d'un utilisateur ? l'autre
# deplus, certain placement comme l'immo change de nature entre t0 et t0+1 (achat cash au depart et non par annuit?)
#########################
load(paste0(reptravail,"/GSE+/R1 CUBE++/R1 OUT/","GSE++_",numerotation,".Rda"))
list_placements_compl<-list_placements

source(file=paste0(reptravail,"/MOCA/FCT/Exp_finance_hist.R"))
sum_cuml<-Exp_fin(M_projets,horiz,salNet,epar)

# fonction pour generer la carte des engagements ? honorer
source(paste0(reptravail,"/MOCA/FCT/Assembl_engagements.R"))
tabl_eur_cont<-engagement(sum_cuml)

# contraintes en % pour l'optimisation
tabl_pourc_cont<-tabl_eur_cont/t(array(rep(sum_cuml,dim(tabl_eur_cont)[1]),dim=c(dim(tabl_eur_cont)[2],dim(tabl_eur_cont)[1])))
# graph sur capital avec/hors engagements
sum_cuml_hors_engag<-sum_cuml-apply(tabl_eur_cont,2,sum)
# plot(sum_cuml,type="l",col="black",ylim=c(0,max(sum_cuml)))
# lines(sum_cuml_hors_engag,type="l",col="red")

#########################
# stripping du profil financier
source(file=paste0(reptravail,"/MOCA/FCT/Reoptimus_striping.R"))
stripping(reptravail,pas_E,sum_cuml_hors_engag)

# formation du GSE++_t0
# constitution de la liste des placements possible pour l'optimum
list_prise<-((tabl_plac$Valeur_t0!=0)|tabl_plac$IND_want)*table_invest$ID# possed? ou voulu pour les R
#list_prise<-c(list_prise,rep(0,length(which(table_invest$annee_empr!=0)))) # on considere les credits non liquides
list_prise<-c(list_prise,1:length(which(table_invest$annee_empr!=0))+length(table_invest$ID)) # on consd?re les credit liquide

# list_prise_liquide<-((tabl_plac$Valeur_t0!=0)|tabl_plac$IND_want)*table_invest$ID*table_invest$Liquide# (possed? ou voulu) et liquide pour les R
# list_prise_liquide<-c(list_prise_liquide,(1:length(which(table_invest$annee_empr!=0))*0)) # pas de prise d'emprunt supplementaire possible

list_placements_opti<-list_placements_compl[list_prise]
# prise uniquement des contraintes sur les actifs shortlisted et liquide
tabl_pourc_cont0<-tabl_pourc_cont[list_prise,]
tabl_eur_cont0<-tabl_eur_cont[list_prise,]
GSEpp_an<-GSE_plac_taxes_an[,,,list_prise] # rendement annuel moyen pour Marko
GSEpp_cuml<-GSE_plac_taxes_cuml[,,,list_prise]
dim(GSEpp_an)

# calcul des optimum Marko bootstrap par actifs, D, aversion
source(file=paste0(reptravail,"/MOCA/FCT/Script_Bootstrap_V4.R"))
Boot_Michaud(reptravail,GSEpp_an,pas_t,Nbboots,Aversion,nom_solution,tabl_pourc_cont0)

# load(paste0(reptravail,"/MOCA/IN/soltot.Rda"))
# D<-1:20
# Tp<-1
# plot(soltot[1,D,Tp,3],ylim=c(0,1))
# for (i in 1:15){
#   lines(soltot[i,D,Tp,3])
# }
# dim(soltot)

########################
# Assemblage du projet et optimum
load(paste0(reptravail,"/MOCA/IN/soltot.Rda"))

dev.off()
source(file=paste0(reptravail,"/MOCA/FCT/Assembl_investV2.R"))
source(paste0(reptravail,"/MOCA/FCT Graphiques/Visualisation_quantiles.R"))
source(paste0(reptravail,"/MOCA/FCT Graphiques/F_graph_optim_mat_result.r"))
for (Avers in 1:length(Aversion)) {
  
  Assembl_invest(reptravail,pas_t,Avers,titre,seuil_filtre,nom_graph,list_placements_opti,soltot,GSEpp_cuml,tabl_pourc_cont0,nom_client)
  load(paste0(reptravail,"/MOCA/OUT/Mat_result_",nom_client,".Rda"))
  
  length(list_placements_opti)
  Mat_result_pourc<-Mat_result/aperm(array(rep(apply(Mat_result,2,sum),length(Mat_result[,1])),dim=c(length(Mat_result[1,]),length(Mat_result[,1]))),c(2,1))
  apply(Mat_result,2,sum)/sum_cuml[1:(length(sum_cuml)-1)]
  
  # verification
  # plot(apply(Mat_result,2,sum),type="o",col="black",ylim=c(50000,500000))
  # lines(sum_cuml,type="l",col="red")
  nom_graph<-paste0("Repartition pour une aversion de ",Aversion[Avers])
  Graph_optim(Mat_result,list_placements_opti,titre,seuil_filtre,nom_graph)
  # Visu_quant(reptravail,apply(Rdt_terme,c(1,3),sum),list_placements_opti)
  # lines(sum_cuml,type="l",col="black")
  Visu_quant(reptravail,apply(Rdt_liquide,c(1,3),sum),list_placements_opti,sum_cuml)
  lines(sum_cuml,type="l",col="black")
  }


