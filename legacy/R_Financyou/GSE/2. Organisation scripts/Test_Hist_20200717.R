# compteur de temps
ptm <- proc.time()
library(xlsx)
library(caTools)
# donnees generales
setwd("E:/")
reptravail<-getwd()
reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")

# Boucle pour les SCR up and down
List_noms_GSE=c("Test_Hist_20200717")
nb_gse=1
for (nb_gse in 1:1) {
sc<-7+(nb_gse-1)*6
######################################################################
# Rt
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 17/7/2020

#chargement de la fonction

source(paste(reptravail,"/R2 CUBE/R2 FCT/HullWhite_PMR_V3.R",sep=""))
# lancement de la fonction
HullWhite("a_sigma_V3.Rda","EIOPA_avril_2018_FRANCE.xlsx",sc,"Corr_ResidAhlgrim_V2.xlsx","Tr-Rt","Tr-deflator","Epsilon.Rda",1000,40,0.5,0.005,reptravail,0.1,-0.1,1)
# calcul du PMR
load(paste(reptravail,"/R2 CUBE/R2 IN/PMR.Rda",sep=""))

load(file=paste0(reptravail,"/R4 CALIBRAGE/R4 OUT/","f0t_liss_",sc,".Rda"))
#ERASE donn?es inutiles
gc()





######################################################################
# Immobilier
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 17/7/2020

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/ImmoBS_PMR_V1.R",sep=""))

# lancement de la fonction
immoBS("Param_immo2.Rda","Tr-Rt.Rda","Epsilon.Rda","Tr-immo",0.5,reptravail)

######################################################################
#ERASE donn?es inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="f0t_liss"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################
# Actions
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 17/7/2020

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/ActionBS_PMR_V2.R",sep=""))

# lancement de la fonction
ActionBS("Param_action.Rda","Tr-Rt.Rda","Epsilon.Rda","Tr-action",0.5,reptravail)

######################################################################
#ERASE donn?es inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="f0t_liss"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################
# ZC
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 17/7/2020

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/ZC_PMR_V3.R",sep=""))

# lancement de la fonction
ZC("a_sigma_V3.Rda","Tr-Rt_PMR.Rda","Tr-ZC",11,0.5,reptravail,sc)

######################################################################
#ERASE donn?es inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="f0t_liss"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################
# Inflation
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 17/7/2020

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/Inflation_V1.R",sep=""))

# lancement de la fonction
Inflation("Tr-Rt_PMR.Rda","Tr-inflation",0.5,reptravail)

######################################################################
#ERASE donn?es inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="f0t_liss"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################



# MEF CUBE
#definition du script R1 CUBE: Mise en Forme du cube GSE au format BH
# Date de mise a jour: 17/7/2020

NbFichieractifs<-5
ListCodeactifs<-c(rep(18,1),rep(0,11),rep(1,1),rep(2,1),rep(3,1),rep(4,1),rep(5,1),rep(7,1),rep(8,1))
ListNomActifs<-c("DEFLATOR",paste("ZC_",seq(1:11)),"EQ_CAPITAL_CHANGE","EQ_DIVIDEND","PROP_CAPITAL_CHANGE","PROP_DIVIDEND","INFLATION","EQUITY_TOTAL_RETURN","PROP_TOTAL_RETURN")
cube<- array(0,dim=c(500*2,40/0.5,19))
#chargement de la fonction
source(paste(reptravail,"/R1 MEFCUBE/R1 FCT/MEFCUBE_V2.R",sep=""))

# lancement de la fonction
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-deflator_PMR.Rda", sep="") ); cube[,,1:1]<-RdtDefl[,];rm(RdtDefl)


load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-immo.Rda", sep="") ); cube[,,19:19]<-RdtImmo[,];rm(RdtImmo)
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-action.Rda", sep="") ); cube[,,18:18]<-RdtActions[,];rm(RdtActions)

load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-inflation.Rda", sep="") ); cube[,,17:17]<-Inflation[,];rm(Inflation)
 cube[,,16:16]<-RdtImmoL[,];rm(RdtImmoL)
 cube[,,15:15]<-RdtImmoP[,];rm(RdtImmoP)
 cube[,,14:14]<-RdtActionsDvd[,];rm(RdtActionsDvd)
 cube[,,13:13]<-RdtActionsP[,];rm(RdtActionsP)
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-ZC.Rda", sep="") ); cube[,,2:12]<-Rdt_ZC[,,];rm(Rdt_ZC)









# lancement de la fonction
#MefCube(ListCodeactifs,ListNomActifs,paste(List_noms_GSE[nb_gse],".csv",sep=""))
save(cube,file = paste(reptravail,"/R1 MEFCUBE/R1 OUT/",paste(List_noms_GSE[nb_gse],".Rda", sep=""), sep="" ) )
} # fin de boucle sur SCR up and down ############################################

# stop the clock
proc.time() - ptm
rm(list=ls())
gc()
######################################################################

