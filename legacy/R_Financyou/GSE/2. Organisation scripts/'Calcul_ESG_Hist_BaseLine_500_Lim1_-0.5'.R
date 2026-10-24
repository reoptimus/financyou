# compteur de temps
ptm <- proc.time()
library(xlsx)
# donnees generales
setwd("E:/")
reptravail<-getwd()
reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")



# Boucle pour les SCR up and down
List_noms_GSE=c("ESG_Hist_BaseLine_500_Lim_1_-0.5")
for (nb_gse in 1:1) {
sc<-2+(nb_gse-1)*6
######################################################################
# Rt
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 18/12/2019

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/HullWhite_V2.R",sep=""))
source(paste(reptravail,"/R2 CUBE/R2 FCT/HullWhite_PMR_V2.R",sep=""))
# lancement de la fonction
HullWhite("a_sigma_V3.Rda","EIOPA_avril_2018_FRANCE.xlsx",sc,"Corr_ResidAhlgrim_V2.xlsx","Tr-Rt","Tr-deflator","Epsilon.Rda",500,60,0.5,0.0025,reptravail,1,-0.5)
# calcul du PMR
source(paste(reptravail,"/R4 CALIBRAGE/R4 FCT/Prime_risque_Caja.R",sep=""))
PMR_func(0.5,60,500,reptravail)
load(paste(reptravail,"/R2 CUBE/R2 IN/PMR.Rda",sep=""))
HullWhite_PMR("a_sigma_V3.Rda","EIOPA_avril_2018_FRANCE.xlsx",2+(nb_gse-1)*6,"Corr_ResidAhlgrim_V2.xlsx","Tr-Rt_PMR","Tr-deflator","Epsilon.Rda",500,60,0.5,0.0025,reptravail,1,-0.5)
#ERASE données inutiles
gc()
######################################################################
# Immobilier
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 18/12/2019

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/ImmoHW_PMR_V1.R",sep=""))

# lancement de la fonction
immo("Param_immo2.Rda","EIOPA_avril_2018_FRANCE.xlsx",sc,"Epsilon.Rda","Tr-immo",0.5,reptravail)

######################################################################
#ERASE données inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################
# Actions
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 18/12/2019

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/ActionBS_PMR_V1.R",sep=""))

# lancement de la fonction
ActionBS("Param_action.Rda","Tr-Rt.Rda","Epsilon.Rda","Tr-action",0.5,reptravail)

######################################################################
#ERASE données inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################
# ZC
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 18/12/2019

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/ZC_V3.R",sep=""))

# lancement de la fonction
ZC("Param_Rt.Rda","Tr-Rt_PMR.Rda","Tr-ZC",40,0.5,reptravail,sc)

######################################################################
#ERASE données inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################
# Inflation
#definition du script R2 CUBE: generation du cube GSE
# Date de mise a jour: 18/12/2019

#chargement de la fonction
source(paste(reptravail,"/R2 CUBE/R2 FCT/Inflation_V1.R",sep=""))

# lancement de la fonction
Inflation("Tr-Rt_PMR.Rda","Tr-inflation",0.5,reptravail)

######################################################################
#ERASE données inutiles
rm(list=ls()[-c(which(ls()=="sc"),which(ls()=="reptravail"),which(ls()=="ptm"),which(ls()=="nb_gse"),which(ls()=="List_noms_GSE"),which(ls()=="PMR"))])
gc()
######################################################################



# MEF CUBE
#definition du script R1 CUBE: Mise en Forme du cube GSE au format BH
# Date de mise a jour: 18/12/2019

NbFichieractifs<-5
ListCodeactifs<-c(rep(18,1),rep(0,40),rep(1,1),rep(2,1),rep(3,1),rep(4,1),rep(5,1),rep(7,1),rep(8,1))
ListNomActifs<-c("DEFLATOR",paste("ZC_",seq(1:40)),"EQ_CAPITAL_CHANGE","EQ_DIVIDEND","PROP_CAPITAL_CHANGE","PROP_DIVIDEND","INFLATION","EQUITY_TOTAL_RETURN","PROP_TOTAL_RETURN")
cube<- array(0,dim=c(250*2,60/0.5,48))
#chargement de la fonction
source(paste(reptravail,"/R1 MEFCUBE/R1 FCT/MEFCUBE_V2.R",sep=""))

# lancement de la fonction
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-deflator.Rda", sep="") ); cube[,,1:1]<-RdtDefl[,];rm(RdtDefl)


load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-immo.Rda", sep="") ); cube[,,48:48]<-RdtImmo[,];rm(RdtImmo)
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-action.Rda", sep="") ); cube[,,47:47]<-RdtActions[,];rm(RdtActions)

load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-inflation.Rda", sep="") ); cube[,,46:46]<-Inflation[,];rm(Inflation)
 cube[,,45:45]<-RdtImmoL[,];rm(RdtImmoL)
 cube[,,44:44]<-RdtImmoP[,];rm(RdtImmoP)
 cube[,,43:43]<-RdtActionsDvd[,];rm(RdtActionsDvd)
 cube[,,42:42]<-RdtActionsP[,];rm(RdtActionsP)
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/","Tr-ZC.Rda", sep="") ); cube[,,2:41]<-Rdt_ZC[,,];rm(Rdt_ZC)









# lancement de la fonction
#MefCube(ListCodeactifs,ListNomActifs,paste(List_noms_GSE[nb_gse],".csv",sep=""))
save(cube,file = paste(reptravail,"/R1 MEFCUBE/R1 OUT/",paste(List_noms_GSE[nb_gse],".Rda", sep=""), sep="" ) )
} # fin de boucle sur SCR up and down ############################################

# stop the clock
proc.time() - ptm
rm(list=ls())
gc()
######################################################################
