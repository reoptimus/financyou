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

HullWhite <- function(param_calib,Mat_resid_name,nom_sortie)
{

  #Paramètres figés pour démonstration
  k <- 0.2
  volHW <- 0.02
  f0 <- read.csv(file=paste(reptravail,"/R2 IN/fzero.csv", sep=""),sep=",",dec = ".", header=FALSE)
  save(k,volHW,f0,file="Param_Rt.Rda")
  
  #chargement du cube des residus correles
  load(paste(reptravail,"/R2 IN/",Mat_resid_name, sep="") )
  #definition de la taille des matrices
  N<-dim(Mat_res) [2]
  T<-dim(Mat_res) [3]
  
  # Chargement des paramètres calibrés
  # contient k,volHW,f0 (vecteur dim=120)
  #load(paste(reptravail,"/R2 IN/",param_calib, sep="") ) #parametres de calibrage des différents processus
  
  ##################################
  # Production de Rt
  ########################
  #Initialisation 
  Rt<-matrix(0,nrow=N,ncol=T)
  
  #Simulations du taux court Rt  pour toutes les périodes de projection
  # Chargement des fonctions utilisées L() et K()
  source("./R2 Fonctions locale/F_K_HullWhite.R")
  source("./R2 Fonctions locale/F_L_HullWhite.R")
  source("./R2 Fonctions locale/F_Rt_HullWhite.R")
  
  for(t in 2:T){
    #Utilisation des formules discrétisées de Hull-White
    Rt[,t]<-Rt_HW(t,Rt[,t-1],k,volHW,f0,Mat_res[4,,t]) # 4 = Taux reel court ; 1 = inflation
  }
  
  #savegarde au format Rdata de la mat de residus correles
  save(Rt, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))
  
  rm(list=c('Rt','k','volHW','Mat_res'))
  #rm(list=ls())
  gc()
  
} #fin fonction
  
