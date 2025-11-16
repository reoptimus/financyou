###############
# fct: ImmoBS
###############
#fonction qui genere les tirages type Black&Scholes pour l'immobilier 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 03/12/2018 par Sébastien Gallet
# modifiée le:
#
# Version : 1
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
#               4 paramètres:MoyenneImmo, VolatiliteImmo, ForceImmo, Immot (valeur de l'indice immo à t=0)
# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

immoBS <- function(param_calib,TrSR,Mat_resid_name,nom_sortie,pas_t,reptravail)
  { #debut fonction
  # param_calib="Param_immo2.Rda"
  # TrSR="Tr-Rt.Rda"
  # Mat_resid_name="Epsilon.Rda"
  # nom_sortie="Tr-immo"
  # pas_t=0.5

  # param fixé dans le code
  # rendement des loyers à t=0
  ImmoL0<-0.02 # pourcentage du taux de loyers annuel
  # Le rendement des loyers evolue comme l'inflation
  # ici on fixe l'inflation en taux continu mais doit être modifié 
  # infl<-0.02

  
# Chargement des fonctions utilisées
source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Blackscholes.R", sep=""))

#chargement du cube des residus correles
load(paste(reptravail,"/R2 CUBE/R2 IN/",Mat_resid_name, sep="") )

#definition de la taille des matrices
N<-dim(Mat_res) [2]
Tf<-dim(Mat_res) [3]

# Chargement des paramètres calibrés
load(paste(reptravail,"/R2 CUBE/R2 IN/",param_calib, sep="") ) #parametres de calibrage de la fonction Vasicek pour immo

# Chargement de la matrice des taux sans risque TrSR
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/",TrSR, sep="") )

##################################
# Rdt Total, Rdt Loyers, Rdt Prix
########################
#Initialisation des actifs pour le calcul du rendement total
RdtImmo<-matrix(0,nrow=N,ncol=Tf)
RdtImmo[,1]<-0

RdtImmoL<-matrix(0,nrow=N,ncol=Tf)
RdtImmoL[,1]<-0

# Le rendement des prix est la différence RdtImmo-RdtImmoL
RdtImmoP<-matrix(0,nrow=N,ncol=Tf)
RdtImmoP[,1]<-0

#Simulations des actifs immobilier pour toutes les périodes de projection
RdtImmo[,2:Tf]<-Blackscholes(Rt[,2:(Tf)],VolatiliteImmo,Mat_res[2,,2:Tf],pas_t)  #1 Tx_Inflation	2 Rdt_Immobilier	3 Tx_reel_long	4 Tx_reel_court	5 Rdt_exces_actions
RdtImmoL[,2:Tf]<-log(1+ImmoL0)*pas_t #conversion du taux annuel en continu puis reduction au pas_t
RdtImmoP[,]<-RdtImmo[,]-RdtImmoL[,]

print("fin de calcul de la tranche Immo")
flush.console()
#savegarde au format Rdata de la mat de residus correles
save(RdtImmo,RdtImmoL,RdtImmoP, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie,".Rda",sep=""))
print("enregistrement de la tranche Immo ds /R1 MEFCUBE/R1 IN/")
flush.console()
rm(list=c('MoyenneImmo','VolatiliteImmo','ForceImmo','Mat_res','ImmoL0'))#'RdtImmo','RdtImmoL','RdtImmoP',
#rm(list=ls())
gc()

} #fin fonction