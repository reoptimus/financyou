###############
# fct: ImmoVasicek
###############
#fonction qui genere les tirages type Vasicek pour l'immobilier 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 31/01/2018 par Sébastien Gallet
# modifiée le: 31/01/2018 par Sébastien Gallet
#
# Version : 2M4 (Vasicek Martingalisé par la méthode 4: correction avec Mu (drift objectif) annuel et sur les rendements cumulés)
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
#               4 paramètres:MoyenneImmo, VolatiliteImmo, ForceImmo, Immot (valeur de l'indice immo à t=0)
# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

immovasicek <- function(param_calib,TrSR,Mat_resid_name,nom_sortie)
  { #debut fonction
  

  # param fixé dans le code
  # rendement des loyers à t=0
  ImmoL0<-0.03
  # Le rendement des loyers evoluent comme l'inflation
  # ici on fixe l'inflation en taux continu mais doit être modifié 
  infl<-0.01
  
# Chargement des fonctions utilisées
source("./R2 Fonctions locale/F_Vacisek1.2.R")

#chargement du cube des residus correles
load(paste(reptravail,"/R2 IN/",Mat_resid_name, sep="") )

#definition de la taille des matrices
N<-dim(Mat_res) [2]
T<-dim(Mat_res) [3]

# Chargement des paramètres calibrés
load(paste(reptravail,"/R2 IN/",param_calib, sep="") ) #parametres de calibrage de la fonction Vasicek pour immo

# Chargement de la matrice des taux sans risque TrSR
load(paste(reptravail,"/R2 IN/",TrSR, sep="") )

##################################
# Rdt Total, Rdt Loyers, Rdt Prix
########################
#Initialisation des actifs pour le calcul du rendement total
RdtImmo<-matrix(0,nrow=N,ncol=T)
RdtImmo[,1]<-0.02 #Immot

RdtImmoL<-matrix(0,nrow=N,ncol=T)
RdtImmoL[,1]<-ImmoL0

# Le rendement des prix est la différence RdtImmo-RdtImmoL
RdtImmoP<-matrix(0,nrow=N,ncol=T)
RdtImmoP[,1]<-RdtImmo[,1]-RdtImmoL[,1]

# Caclcul du drift objectif pour martingaliser le processus Vasicek: méthode 2 cumulée
VolatiliteImmo2<-VolatiliteImmo*((1-exp(-2*ForceImmo))/(2*ForceImmo))^0.5
Mu<-0
SigmaMu<-0
SumRdtImmo<-matrix(0,nrow=N,ncol=1)
SumRt<-matrix(0,nrow=N,ncol=1)

#pour k=1
k<-1
Mu<-(VolatiliteImmo2^2)/2)/(1-exp(-ForceImmo))#+(log(sum(exp(-Rt[,1]))/N)
RdtImmo[,k]<-Vacisek1(RdtImmo[,1],ForceImmo,Mu,VolatiliteImmo,Mat_res[2,,k]) # 2 = immo depend de la matrice de correlation
RdtImmoP[,k]<-(RdtImmo[,k]-RdtImmoL[,1]*exp(infl))/(1-RdtImmoL[,1])
RdtImmoL[,k]<-RdtImmoL[,1]*(exp(infl)-RdtImmoP[,k]) #infl en taux continu moyen sur l'année
SumRt[,1]<-SumRt[,1]+Rt[,k]

#Simulations des actifs pour toutes les périodes de projection
for(k in 2:T){
  #Simulations avec conversion du taux continu en taux annuel pour la formule discrète
  SumRdtImmo[,1]<-SumRdtImmo[,1]+RdtImmo[,k-1]
  SumRt[,1]<-SumRt[,1]+Rt[,k]
  SigmaMu<-SigmaMu+Mu
  Mu<-(-log(sum(exp(SumRdtImmo[,1]*exp(-ForceImmo)-SumRt[,1]))/N)-k*(VolatiliteImmo2^2)/2)/(1-exp(-ForceImmo))-SigmaMu
  RdtImmo[,k]<-Vacisek1(RdtImmo[,k-1],ForceImmo,Mu,VolatiliteImmo,Mat_res[2,,k]) # 2 = immo depend de la matrice de correlation
  RdtImmoP[,k]<-(RdtImmo[,k]-RdtImmoL[,k-1]*exp(infl))/(1-RdtImmoL[,k-1])
  RdtImmoL[,k]<-RdtImmoL[,k-1]*(exp(infl)-RdtImmoP[,k]) #infl en taux continu moyen sur l'année
  }

#savegarde au format Rdata de la mat de residus correles
save(RdtImmo,RdtImmoL,RdtImmoP, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))

rm(list=c('RdtImmo','RdtImmoL','RdtImmoP','MoyenneImmo','VolatiliteImmo','ForceImmo','Mat_res','infl','ImmoL0','Mu','SumRdtImmo','SumRt','SigmaMu'))
#rm(list=ls())
gc()

} #fin fonction