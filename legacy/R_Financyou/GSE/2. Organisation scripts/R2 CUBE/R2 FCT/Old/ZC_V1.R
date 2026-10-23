###############
# fct: ZC
###############
#fonction qui genere les taux courts de la formule d'Hull-White 
#servant de base aux autres calculs (Immo/action)
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 7/12/2017 par Fabrice Borel-Mathurin
# modifiée le: 06/02/2018 par Sebastien Gallet
#
# Version : 1
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
# Mat_res = Matrice des residus correlés Epsilon
#               3 paramètres:k, VolHW, f (taux forward instantanés f(0,t))
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

ZC <- function(param_calib,Taux_ss_risque,nom_sortie)
{
  #param_calib<-"Param_Rt.Rda"
  #Taux_ss_risque<-"Tr-Rt.Rda"
  #nom_sortie<-"Tr-ZC"
  #duration utilisée pour troncquer la matrice et pour n'utiliser que la partie vrai à savoir quand t+d<T
  d<-40 
  
  #Paramètres figés pour démonstration
  k <- 0.2
  volHW <- 0.1
  f0 <- read.csv(file=paste(reptravail,"/R2 IN/fzero.csv", sep=""),sep=",",dec = ".", header=FALSE)
  ZC_t<-read.csv(file=paste(reptravail,"/R2 IN/ZC.csv", sep=""),sep=",",dec = ".", header=FALSE)
  save(k,volHW,f0,ZC,file="Param_Rt.Rda")
  
  # Chargement des fonctions utilisées L() et K()
  source(paste(reptravail,"/R2 Fonctions locale/F_K_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 Fonctions locale/F_L_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 Fonctions locale/F_Rt_HullWhite.R",sep=""))

  # Chargement des paramètres calibrés
  # contient k,volHW,f0 (vecteur dim=120)
  #load(paste(reptravail,"/R2 IN/",param_calib, sep="") ) #parametres de calibrage des différents processus
  
  
  #chargement au format Rdata des taux sans risques Rt correles depuis le dossier "IN"
  load(paste(reptravail,"/R2 IN/",Taux_ss_risque, sep="") )
  #definition de la taille des matrices
  N<-dim(Rt) [1]
  T<-dim(Rt) [2]
  
  #mise en forme en 3D
  d_tot=T-1 #T-d ? #calcul sur la duration maximale
  Rt3D<-array(rep(Rt,d_tot),dim=c(N,T,d_tot))
  
  #libere la mémoire vive inutile
  rm(list=c('Rt'))
  gc()
  
  ######################
  #calcul de P(t,T)
  ######################
  #méthode par répétition de l'information sur les dimensions manquantes
  #puis calcul termes à termes des matrices 3D ( n * T * (T-1))
  List_Tmoinst<-(1:d_tot) #taille de la dimension duration (T-t)
  K3D<-array(rep(K(List_Tmoinst,k),T*N),dim=c(d_tot,T,N))
  K3D<-aperm(K3D,c(3,2,1))
  #dim(K3D[,,])

  L3D<-array(rep(L((1:T),volHW,k),d_tot*N),dim=c(T,d_tot,N))
  L3D<-aperm(L3D,c(3,1,2))
  
  f03D<-array(rep(f0[,1],d_tot*N),dim=c(T,d_tot,N))
  f03D<-aperm(f03D,c(3,1,2))
  
  PZC_tT<-array(0,dim=c(N,T,d_tot))
  PZC_tT<-exp(-K3D^2/2*L3D+K3D*f03D-Rt3D)
  
  #libere la mémoire vive inutile
  rm(list=c('K3D','L3D','f03D','Rt3D'))
  gc()
 
  #calcul de P0T (dépend de t et d car T=t+d)
  
  #!!!faire un test sur la taille de ZC!!!
  ZC2D<-array(rep(ZC_t[,1],d_tot),dim=c(T,d_tot))
  tplusd<-array(rep(1:T,d_tot),dim=c(T,d_tot))+aperm(array(rep(1:d_tot,T),dim=c(d_tot,T)))
  P0T<- array(rep((1+ZC2D)^(-tplusd),N),dim=c(T,d_tot,N))
  P0T<-aperm(P0T,c(3,1,2))
  
  #calcul de P0t ne dépend que de t
  t_liste<-1:T
  P0t<- array(rep((1+ZC_t[,1])^(-t_liste),N*d_tot),dim=c(T,N,d_tot))
  P0t<-aperm(P0t,c(2,1,3))

  P0T_P0t<-P0T/P0t
  PZC_tT<-PZC_tT*P0T_P0t
  Rdt_ZC<-PZC_tT[1:N,1:T,1:d]
  
  #libere la mémoire vive inutile
  rm(list=c('ZC_t','P0T_P0t','P0T','P0t','ZC2D','t_liste'))
  gc()
  
  #savegarde au format Rdata de la mat des ZC
  save(Rdt_ZC, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))

  #libere la mémoire vive inutile
  rm(list=c('PZC_tT','k','volHW','d','d_tot','Rdt_ZC'))
  #rm(list=ls())
  gc()
  
} #fin fonction

