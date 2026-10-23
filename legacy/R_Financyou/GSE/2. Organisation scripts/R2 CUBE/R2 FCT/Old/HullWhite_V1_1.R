###############
# fct: HullWhite
###############
#fonction qui genere les taux courts de la formule d'Hull-White 
#servant de base aux autres calculs (Immo/action)
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 7/12/2017 par Fabrice Borel-Mathurin
# modifiée le: 16/01/2018 par Fabrice Borel-Mathurin
#
# Version : 1.1
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
#               3 paramètres:k, VolHW, f (taux forward instantanés f(0,t))
# Mat_res = Matrice des residus correlés Epsilon
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

HullWhite <- function(param_calib,ForwardInst,Mat_resid_name,nom_sortie)
{
  #Paramètres figés pour démonstration
  k <- 0.2
  volHW <- 0.1
  
  # Chargement des fonctions utilisées
  source("./R2 Fonctions locale/F_Vacisek1.R")
  
  #chargement du cube des residus correles
  load(paste(reptravail,"/R2 IN/",Mat_resid_name, sep="") )
  
  # Chargement des paramètres calibrés
  load(paste(reptravail,"/R2 IN/",param_calib, sep="") ) #parametres de calibrage des différents processus
  
  # Chargement du vecteur de taux forward instantanés à t=0
  load(paste(reptravail,"/R2 IN/",f0, sep="") )
  
  ##################################
  # Production de Rt
  ########################
  #Initialisation 
  Rt<-matrix(0,nrow=N,ncol=T)
  
  #Simulations du taux court Rt  pour toutes les périodes de projection
  for(t in 2:T){
    #Utilisation des formules discrétisées de Hull-White
    Rt[,t]<-Rt_HW(N,t,Rt[,t-1],k,volHW,f0,Mat_res[1,,t]) # 1 = A faire vérifier, mais normalement les tirages pour les taux sont en 1?
  }
  
  
  #savegarde au format Rdata de la mat de residus correles
  save(Rt, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))
  
  rm(list=c('Rt','k','volHW','Mat_res'))
  #rm(list=ls())
  gc()
  
} #fin fonction
  
