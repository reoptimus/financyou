###############
# fct: ImmoHW_PMR
###############
#fonction qui genere la diffusion HW pour les prix de l'immobilier 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 07/01/2020 par Sébastien Gallet
# modifiée le: 
#
# Version : 2 (HW marting avec loyers fixes et inflation loyers flat)
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
#               4 paramètres:MoyenneImmo, VolatiliteImmo, ForceImmo, Immot (valeur de l'indice immo à t=0)
# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
# PMR...chargement en dur dans le code
###########################################

library(abind)
library(xlsx)

immo <- function(param_calib,Param_EIOPA,sc,Mat_resid_name,nom_sortie,delta_t,reptravail)
  { #debut fonction
  # param_calib="Param_immo2.Rda"
  # Param_EIOPA<-"EIOPA_avril_2018_FRANCE.xlsx"
  # sc=2
  # Mat_resid_name="Epsilon.Rda"
  # nom_sortie="Tr-immo"
  # delta_t=0.5
  # donnees generales
  # setwd("E:/")
  # reptravail<-getwd()
  # reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")
  # NB=dim(Mat_res)[2]
  
  # Chargement des fonctions utilisées
  #source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Blackscholes_PMR.R", sep=""))
  #load(paste(reptravail,"/R2 CUBE/R2 IN/PMR.Rda", sep="") )

  #chargement du cube des residus correles
  load(paste(reptravail,"/R2 CUBE/R2 IN/",Mat_resid_name, sep="") )
  
  # Chargement des paramètres calibrés
  load(paste(reptravail,"/R2 CUBE/R2 IN/",param_calib, sep="") ) #parametres de calibrage de la fonction Vasicek pour immo
  sigma2<-VolatiliteImmo
  a2<-ForceImmo
  
  ## f0t pour pas_discr #############################
  #chargement de la courbe des taux (EIOPA) et recalcul des courbes f0t et P0t
  source(paste(reptravail,"/R4 CALIBRAGE/R4 FCT/","Calib_Tauxf0_V2.2.R",sep=""))
  
  #definition de la taille des matrices
  NB<-dim(Mat_res) [2]
  Tf<-dim(Mat_res) [3]
  alea_R2<-Mat_res[6,,]
  alea_r2<-Mat_res[2,,]
  
  # recalcul de la courbe des taux. A optimiser mais assure la coherence
  Calib_Tauxf0(Param_EIOPA,reptravail,delta_t,sc)
  
  # chargement des courbes EIOPA
  load(file=paste0(reptravail,"/R4 CALIBRAGE/R4 OUT/","Prix_P0t_interp_",sc,".Rda"))
  load(file=paste0(reptravail,"/R4 CALIBRAGE/R4 OUT/","f0t_liss_",sc,".Rda"))
  
  # initialisation param
  r0<-array(rep(f0t_liss[2],NB),dim=c(NB))
  r0_2<-r0
  r0_1<-r0
  Tp<-delta_t
  tp<-0
  # param fixé dans le code
  Infl<-log(1+0.00)*delta_t # % d'inflation sur les loyers immobiliers hors infl monÃ©taire sur la periode
  L0_P0<-log(1+0.01)*delta_t #% de loyer annuel en taux continu sur la periode
  Loyer0<-array(exp(L0_P0),dim=c(NB,1)) # vecteur
  
  ##################################
  # Rdt Total, Rdt Loyers, Rdt Prix
  ########################
  #Initialisation des actifs pour le calcul du rendement total
  RdtImmo<-matrix(0,nrow=NB,ncol=Tf)
  RdtImmo[,1]<-0
  
  RdtImmoL<-matrix(0,nrow=NB,ncol=Tf)
  RdtImmoL[,1]<-0
  
  # Le rendement des prix est la différence RdtImmo-RdtImmoL
  RdtImmoP<-matrix(0,nrow=NB,ncol=Tf)
  RdtImmoP[,1]<-0
  RdtImmoCumul<-matrix(0,nrow=NB,ncol=1)
  
  #################################
  # diffusion de R(t) et r(t)
  #################################
  k_control_2<-array(0,dim=c(Tf))
  k_control_3<-array(0,dim=c(Tf))
  k_control_4<-array(0,dim=c(Tf))
  K2T_t2a<-(1-exp(-2*a2*delta_t))/(2*a2)
  K2T_t<-(1-exp(-a2*delta_t))/a2
  eta2<-(sigma2/a2)*(delta_t-2*K2T_t+K2T_t2a)^0.5
  
  for (i in 1:(Tf)) {
    ##################################
    # calcul pour R(t,T) HW immo
    ##################################

    ###########################################
    # optimisation de kimmo pour etre martingal
    kimmo<-f0t_liss[i]+PMR[i]*sigma2/a2 #r0_2*(a2+r0_1)#f0t_liss[i]
    k_control_2[i]<-max(kimmo)
    # k_control_3[i]<-min(kimmo)
    # k_control_4[i]<-mean(kimmo)
    # fin d'optimisation de k(t,t+1) pour etre martingal
    ###########################################
    
    RdtImmo[,i]<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
    r0_2<-r0_2*exp(-a2*delta_t)+kimmo*(1-exp(-a2*delta_t))+sigma2*K2T_t2a^0.5*alea_r2[,i] 
    
    #RdtImmoL[,i]<-log(1+L0_P0*exp(-RdtImmoCumul+i*Infl)) #loyer formule capitalisee
    RdtImmoL[,i]<-L0_P0+i*Infl
    RdtImmoP[,i]<-RdtImmo[,i]-RdtImmoL[,i] # prix
    RdtImmoCumul<-RdtImmoCumul+RdtImmo[,i]
    
    # calcul de parametre pour la boucle suivante
    Tp<-Tp+delta_t
    tp<-tp+delta_t #tp utilise pour les actifs, n'Ã©volue pas au court de la diffusion
  } #fin boucle i sur les periodes

#savegarde au format Rdata de la mat de residus correles
save(RdtImmo,RdtImmoL,RdtImmoP, file=paste0(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie,".Rda"))
plot(k_control_2,ylim=c(-0.1,0.1),type="l",col="blue")
# lines(k_control_3,col="red")
# lines(k_control_4,col="black")
rm(list=ls()[-c(which(ls()=="k_control_2"),which(ls()=="reptravail"),which(ls()=="sc"))])
gc()

} #fin fonction