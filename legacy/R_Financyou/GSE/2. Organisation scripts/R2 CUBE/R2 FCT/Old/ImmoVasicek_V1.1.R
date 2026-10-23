###############
# fct: ImmoVasicek
###############
#fonction qui genere les tirages type Vasicek pour l'immobilier 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 25/10/2017 par Sébastien Gallet
# modifiée le: 16/11/2017 par Sébastien Gallet
#
# Version : 1.1
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
#               4 paramètres:MoyenneImmo, VolatiliteImmo, ForceImmo, Immot (valeur de l'indice immo à t=0)

# param fixé dans le code
# rendement des loyers à t=0
ImmoL0<-0.02
# Le rendement des loyers evolue comme l'inflation
# ici onfixe l'inflation mais doit être mofdifié 
infl<-0.02

# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

# Fonction pour generation nombre aletoire correle
immovasicek <- function(param_calib,Mat_resid_name,nom_sortie)
  { #debut fonction

# Chargement des fonctions utilisées
source("./R2 Fonctions locale/F_Vacisek1.R")

#chargement du cube des residus correles
load(paste(reptravail,"/R2 IN/",Mat_resid_name, sep="") )

# Chargement des paramètres calibrés
load(paste(reptravail,"/R2 IN/",param_calib, sep="") ) #parametres de calibrage de la fonction Vasicek pour immo

##################################
# Rdt Total, Rdt Loyers, Rdt Prix
########################
#Initialisation des actifs pour le calcul du rendement total
RdtImmo<-matrix(0,nrow=N,ncol=T)
RdtImmo[,1]<-Immot

RdtImmoL<-matrix(0,nrow=N,ncol=T)
RdtImmoL[,1]<-ImmoL0

# Le rendement des prix est la différence RdtImmo-RdtImmoL
RdtImmoP<-matrix(0,nrow=N,ncol=T)
RdtImmoP[,1]<-RdtImmo[,1]-RdtImmoL[,1]

#Simulations des actifs pour toutes les périodes de projection
for(k in 2:T){
  #Simulations
  RdtImmo[,k]<-Vacisek1(RdtImmo[,k-1],ForceImmo,MoyenneImmo,VolatiliteImmo,Mat_res[2,,k]) # 2 = immo depend de la matrice de correlation
  RdtImmoP[,k]<-(RdtImmo[,k]-RdtImmoL[,k-1]*(1+infl))/(1-RdtImmoL[,k-1])
  #RdtImmoP[,k]<-RdtImmo[,k]-RdtImmoL[,k]
  RdtImmoL[,k]<-RdtImmoL[,k-1]*(1+infl-RdtImmoP[,k])

}


#savegarde au format Rdata de la mat de residus correles
save(RdtImmo,RdtImmoL,RdtImmoP, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))

rm(list=c('RdtImmo','RdtImmoL','RdtImmoP','MoyenneImmo','VolatiliteImmo','ForceImmo','Mat_res','infl','ImmoL0'))
#rm(list=ls())
gc()

} #fin fonction