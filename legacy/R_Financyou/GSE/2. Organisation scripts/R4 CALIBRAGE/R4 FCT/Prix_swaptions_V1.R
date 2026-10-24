###########################################
# fct: Prix_swaptions (voir fiche sur les tauxV4)
###########################################
#fonction qui genere les prix des swaptions par formule fermée
#à partir des données EIOPA, ZC marché, paramètres (a,sigma)
#
# crée le: 26/06/2018 par Sébastien Gallet
# modifiée le:14/11/2018
#
# Version : 2
#
# variables d entree#######################
# t la maturité du swaption
# Tdeb debut des flux
# S fin des flux et echange du nominal
# n temps en année entre deux échanges
# X strike
# a paramètre de retour à la moyenne Vasicek
# sigma, Volatilité implicite
# f0, forward instantanné issu de la courbe EIOPA
# r0 taux court à Tdeb=0
# P0t, prix des obligation observées sur la marché pour différentes maturité (années entières)
###########################################

Prix_swaptions_FF <- function(t,Tdeb,S,n,X,a,sigma,f0t,r0,P0t,reptrav)
{
  
  #Paramètres figés pour test à effacer###########
  # reptravail<-'\\\\intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG_V2/2. Organisation scripts/'
  # Mat_resid_name<-'Epsilon.Rda'
  # nom_sortie_P0t<-"Prix_P0t_interp.Rda"
  # nom_sortie_f0t<-"f0t_liss.Rda"
  # reptrav<-reptravail
  # load(file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/",nom_sortie_P0t,sep=""))
  # load(file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/",nom_sortie_f0t,sep=""))
  # load(paste(reptravail,"R2 CUBE/R2 IN/",Mat_resid_name, sep="") )
  # t<-0 
  # Tdeb<-1
  # S<-5
  # n<-0.5 # swaps jambes de n ans ATTENTION, doit correspondre au pas_t
  # P0t<-P0t_interp
  pas<-1/round(length(f0t_liss)/(length(Mat_EIOPA[,2])+1)) #s'assurer que les points EIOPA sont toujours sur 150 ans
  # X<-0.005 #(P0t[Tdeb/pas+1]-P0t[S/pas+1])/sum(P0t[Tdeb/pas+1:S/pas+1])
  # a <- 0.01
  # sigma <- 0.005
  # f0t<-f0t_liss
  # r0<-f0t[1]
  # Mat_resid<-Mat_res
  # ##############################################
  
  # Chargement des fonctions utilisées L(), K() et A()
  source(paste(reptrav,"R2 CUBE/R2 Fonctions locale/F_K_HullWhite.R",sep=""))
  source(paste(reptrav,"R2 CUBE/R2 Fonctions locale/F_L_HullWhite.R",sep=""))
  source(paste(reptrav,"R2 CUBE/R2 Fonctions locale/F_A_HullWhite.R",sep=""))
  ##############################################
  
  # calcul de r*################################
  # formation de ci
  nb_t0_ti<-1:((S-Tdeb)/n)
  ci<-array(1,dim=c(length(nb_t0_ti),1))*n*X
  ci[length(nb_t0_ti)]<-ci[length(nb_t0_ti)]+1
  
  #initialisation
  Ai<-array(0,dim=c(length(nb_t0_ti),1))
  Ki<-array(0,dim=c(length(nb_t0_ti),1))
  
  #calcul
  Ai<-A(Tdeb,(nb_t0_ti*n+Tdeb),a,sigma,P0t,f0t,pas)
  Ki<-K(nb_t0_ti*n,a)
  #recherche du zero de la fonction Uniroot_r
  source(paste(reptrav,"/R4 CALIBRAGE/R4 Commande locale/Uniroot_r.R",sep=""))    
  r_opt<-uniroot(Uniroot_r,b=Ai,k=Ki,c=ci , interval=c(-2,2),tol=0.0001,extendInt="yes")$root
  #############################################

  #calcul de Qi -> vecteur
  Qi<-array(0,dim=c(length(nb_t0_ti),1))
  Qi<-Ai*exp(-Ki*r_opt)
  # verif sum(Qi*ci)=1
  
  #calcul P(0,Tdeb) obligation maturité Tdeb et S
  PT<-A(0,Tdeb,a,sigma,P0t,f0t,pas)*exp(-K(Tdeb,a)*r_opt)

  #calcul des prix de swaptions################
  PSw<-0 #initialisation
  # formation de ci
  ci<-n*rep(X,length(Qi))
  ci[length(Qi)]<-ci[length(Qi)]+1
  
  for (ti in 1:((S-Tdeb)/n)) { # ti est ici un increment entre Tdeb et S par pas de n
    PS<-A(0,ti*n+Tdeb,a,sigma,P0t,f0t,pas)*exp(-K(ti*n+Tdeb,a)*r_opt)
    #calcul sigmap
    sigmap<-sigma*((1-exp(-2*a*(Tdeb)))/(2*a))^0.5*K(ti*n,a)
    #calcul de h
    h<-(1/sigmap)*log(PS/(PT*Qi[ti]))+sigmap/2
    # calcul de ZBP(t,Tdeb,ti,Qi)
    ZBP<-Qi[ti]*pnorm(-h+sigmap, mean = 0, sd = 1)*PT-PS*pnorm(-h, mean = 0, sd = 1)
    # calcul du prix du swaption
    PSw<-PSw+ci[ti]*ZBP
  }
  #############################################
  
  #libere la mémoire vive inutile
  rm(list=c('nb_t0_ti','ci','Ai','Qi','PT','r_opt','sigmap','PS','sigma','h','ZBP'))
  #rm(list=ls())
  gc()
  
  return(PSw)
  
} #fin fonction
  
