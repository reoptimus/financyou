###############
# fct: ZC
###############
#fonction qui genere les ZC
#
#à partir des des Rt et f0t_liss
#
# crée le: 7/12/2017 par Fabrice Borel-Mathurin
# modifiée le: 06/02/2018 par Sebastien Gallet
#
# Version : 1
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
# Mat_res = Matrice des residus correlés Epsilon
#               3 paramètres:k, VolHW, f (taux forward instantanés f(0,t)), ZC(t) les prix des ZC à t0
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

ZC <- function(param_calib,Taux_ss_risque,nom_sortie,d,pas,reptravail,sc)
{
    #################################### A effacer
  #Paramètres figés pour démonstration
  #param_calib<-"a_sigma_V3.Rda"
  #Taux_ss_risque<-"Tr-Rt.Rda"
  #nom_sortie<-"Tr-ZC"
  #duration utilisée pour troncquer la matrice et pour n'utiliser que la partie vrai à savoir quand t+d<Tf
  
  print("début du calcul des ZC")
  flush.console()

  load(file=paste0(reptravail,"/R2 CUBE/R2 IN/",param_calib)) #parametre calibre pour les taux H&W
  k <- a
  volHW <- sigma
  load(file=paste(reptravail,"/R4 CALIBRAGE/R4 OUT/f0t_liss_",sc,".Rda", sep=""))
  #f0t_liss ds l'environnement global
  
  #P(0,t) var globale
  load(file=paste(reptravail,"/R4 CALIBRAGE/R4 OUT/Prix_P0t_interp_",sc,".Rda", sep=""))
  ZC_t<-P0t_interp
  
  # Chargement des fonctions utilisées L() et K()
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_K_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_L_HullWhite.R",sep=""))
  #source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rt_HullWhite.R",sep=""))

 
  #chargement au format Rdata des taux sans risques Rt correles depuis le dossier "IN"
  #Taux_ss_risque<-"Tr-Rt.Rda"
  load(paste(reptravail,"/R1 MEFCUBE/R1 IN/",Taux_ss_risque, sep="") )
  try(Rt<-Rt_PMR, silent=TRUE) #fonctionne aussi bien pour RN ou PMR

  #definition de la taille des matrices
  N<-dim(Rt) [1]
  Tf<-dim(Rt) [2]
  t_liste<-1:Tf
  
  #mise en forme en 3D
  d_tot=d #Tf-d ? #calcul sur la duration maximale
  Rt3D<-array(rep(Rt,d_tot),dim=c(N,Tf,d_tot))
  
  #libere la mémoire vive inutile
  rm(list=c('Rt'))
  gc()

  ######################
  #calcul de P(t,Tf)
  ######################
  #méthode par répétition de l'information sur les dimensions manquantes
  #puis calcul termes à termes des matrices 3D ( n * Tf * (Tf-1))
  List_Tmoinst<-(1:d_tot) #taille de la dimension duration (Tf-t)
  K3D<-array(rep(K(List_Tmoinst,k),Tf*N),dim=c(d_tot,Tf,N))
  K3D<-aperm(K3D,c(3,2,1))
  #dim(K3D[,,])

  L3D<-array(rep(L(t_liste*pas,volHW,k),d_tot*N),dim=c(Tf,d_tot,N))
  L3D<-aperm(L3D,c(3,1,2))
  
  f03D<-array(rep(f0t_liss[t_liste],d_tot*N),dim=c(Tf,d_tot,N))
  f03D<-aperm(f03D,c(3,1,2))
  
  PZC_tT<-array(0,dim=c(N,Tf,d_tot))
  PZC_tT<-exp(-K3D^2/2*L3D+K3D*(f03D-Rt3D))  #calcul des prix ZC directement en 3D pour (N,Tf,d)
  
  #libere la mémoire vive inutile
  rm(list=c('K3D','L3D','f03D','Rt3D'))
  gc()
 
  #calcul de P0T (dépend de t et d car Tf=t+d)
  tplusd<-array(rep(t_liste,d_tot),dim=c(Tf,d_tot))+aperm(array(rep((1:d_tot)/pas,Tf),dim=c(d_tot,Tf))) #increment et non un temps
  ZC_t2D<-array(rep(ZC_t[tplusd]),dim=c(Tf,d_tot))
  P0T<- array(rep(ZC_t2D,N),dim=c(Tf,d_tot,N))
  P0T<-aperm(P0T,c(3,1,2))
  
  #calcul de P0t ne dépend que de t  
  P0t<- array(rep(ZC_t[t_liste],N*d_tot),dim=c(Tf,N,d_tot))
  P0t<-aperm(P0t,c(2,1,3))

  P0T_P0t<-P0T/P0t
  
  PZC_tT<-PZC_tT*P0T_P0t
  Rdt_ZC<-PZC_tT[1:N,1:Tf,1:d]
  
  #libere la mémoire vive inutile
  rm(list=c('ZC_t','P0T_P0t','P0T','P0t','ZC_t2D','t_liste','tplusd'))
  gc()
  
  print("fin de calcul des ZC")
  flush.console()
  
  #savegarde au format Rdata de la mat des ZC
  save(Rdt_ZC, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie,".Rda",sep=""))

  print("Sauvegarde des tranches de ZC ds /R1 MEFCUBE/R1 IN/")
  flush.console()
  
  #libere la mémoire vive inutile
  rm(list=c('PZC_tT','k','volHW','d','d_tot','Rdt_ZC'))
  #rm(list=ls())
  gc()
  
} #fin fonction

