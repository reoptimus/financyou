###########################################
# fct: Prix_swaptions
###########################################
#fonction qui genere les prix des swaptions par calcul direct sur les tirages
#à partir des données EIOPA, ZC marché, paramètres (a,sigma), matrice des residus
#
# crée le: 03/09/2018 par CHC
# modifiée le:
#
# Version : 2
#
# variables d entree#######################
# t la maturité du swaption
# T debut des flux
# S fin des flux et echange du nominal
# n temps en année entre deux échanges
# X strike
# a paramètre de retour à la moyenne Vasicek
# sigma, Volatilité implicite
# f0, forward instantanné issu de la courbe EIOPA
# r0 taux court à T=0
# P0t, prix des obligation observées sur la marché pour différentes maturité (années entières)
# Mat_resid, la matrice des residus correles pour generer la matrice Rt (taux courts)
# pas_t , le pas de temps du GSE
###########################################

Prix_swaptions_MC <- function(t,Tdeb,S,n,X,a,sigma,f0t,P0t,reptrav,Mat_res)
{
  #Paramètres figés pour test à effacer
  # reptravail<-"//intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG_V2/2. Organisation scripts"
  # Mat_resid_name<-'Epsilon.Rda'
  # nom_sortie_P0t<-"Prix_P0t_interp.Rda"
  # nom_sortie_f0t<-"f0t_liss.Rda"
  # load(file=paste(reptravail,"/R4 CALIBRAGE/R4 OUT/",nom_sortie_P0t,sep=""))
  # load(file=paste(reptravail,"/R4 CALIBRAGE/R4 OUT/",nom_sortie_f0t,sep=""))
  # load(paste(reptravail,"/R2 CUBE/R2 IN/",Mat_resid_name, sep="") )
  # length(P0t_interp)
  # dim(Mat_res)
  # 
  # t<-0
  # Tdeb<-1
  # S<-20
  # n<-0.5 # swaps jambes de n ans ATTENTION, doit correspondre au pas_t
  # X<-0.02 #(P0t[Tdeb/pas+1]-P0t[S/pas+1])/sum(P0t[Tdeb/pas+1:S/pas+1])
  # a <- 0.0058333
  # sigma <- 0.006875
  # f0t<-f0t_liss
  # P0t<-P0t_interp
  # reptrav<-reptravail
  # Mat_resid<-Mat_res[1,,]

  pas<-1/round(length(f0t)/151)
  r0<-f0t[1]
  nb_pas<-(S/pas+1)
  
  # si besoin, création de la matrice des tirages aleatoire en local
  # N<-2000 #dim(Mat_resid1) [2]
  # Mat_resid<-array(rnorm(nb_pas*N/2, mean = 0, sd = 1),dim=c(N/2,nb_pas))
  # Mat_resid<-rbind(Mat_resid,-Mat_resid) #variables antitetiques

  ##################################
  # Production de Rt (taux instantanés) en fonction de 
  ##################################
  #Initialisation 
  #Mat_resid
  Rt<-matrix(0,nrow=length(Mat_resid[,1]) ,ncol=nb_pas)
  Rt[,1]<-r0
  
  # Chargement des fonctions utilisées L() et K()
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_K_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_L_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rt_HullWhite.R",sep=""))
  
  ###############################################  
  #Simulations du taux court Rt  pour toutes les périodes de projection
  for(i in 1:(nb_pas-1)){
    #Utilisation des formules discrétisées de Hull-White
    Rt[,i+1]<-Rt_HW(i,Rt[,i],a,sigma,f0t,Mat_resid[,i],pas)
  }
  
  # plot(apply(Rt,2,mean),ylim=c(-0.05,0.05),col="red",main=paste("a=",a," et sigma=",sigma,sep="")) #pour control visuel
  # for (i in 1:20) {lines(Rt[i,],col="grey")}
  
  ###############################################
  #calcul du prix du swaption en fonction de Rt (matrice tirages), a (force de rappel) , sigma (vol), f0t, P0t
  
  Prix_ZC <- function(t2,T2,a2,sigma2,f02,P02,pas2)
  {
    B<-1/a2*(1-exp(-a2*(T2-t2)))
    A<-P02[T2/pas2+1]/P02[t2/pas2+1]*exp(B*f02[t2/pas2+1]-sigma2^2/(4*a2)*B^2*(1-exp(-2*a2*t2)))
    Prix_ZC1<-A*exp(-B*Rt[,t2/pas2+1])
    return(Prix_ZC1)
  }
  
  # Prix_ZC(1,10,a,sigma,f0t,P0t,pas)[1]  : test

  Valeur_swap_payeur <- function(T2,S2,n2,X2,a2,sigma2,f0t2,P0t2,pas2)
  {
    #1ere etape: Calcul du taux swap forward
    denom<-0
    for (i in 1:((S2-T2)/n2))
    {
      denom<-denom+n2*Prix_ZC(T2,T2+i*n2,a2,sigma2,f0t2,P0t2,pas2) 
    }
    taux_swap<-(Prix_ZC(T2,T2,a2,sigma2,f0t2,P0t2,pas2)-Prix_ZC(T2,S2,a2,sigma2,f0t2,P0t2,pas2))/denom #chgt 0 en t (premier terme)
    
    #Calcul du payoff actualisé (notionnel =1)
    fra<-0
    for (i in 1:((S2-T2)/n2))
    {
      fra<-fra+n2*Prix_ZC(T2,T2+i*n2,a2,sigma2,f0t2,P0t2,pas2)*(taux_swap-X2) #max((taux_swap-X2),0)  ???
    }
    fra
  }
  
  Valeur_swap_receveur <- function(T2,S2,n2,X2,a2,sigma2,f0t2,P0t2,pas2)
  {
    #1ere etape: Calcul du taux swap forward
    denom<-0
    for (i in 1:((S2-T2)/n2))
    {
      denom<-denom+n2*Prix_ZC(T2,T2+i*n2,a2,sigma2,f0t2,P0t2,pas2)
    }
    taux_swap<-(Prix_ZC(T2,T2,a2,sigma2,f0t2,P0t2,pas2)-Prix_ZC(T2,S2,a2,sigma2,f0t2,P0t2,pas2))/denom #chgt 0 en t (premier terme)
    #Calcul du payoff actualisé (notionnel =1)
    fra<-0
    for (i in 1:((S2-T2)/n2))
    {
      fra<-fra-n2*Prix_ZC(T2,T2+i*n2,a2,sigma2,f0t2,P0t2,pas2)*(taux_swap-X2)
    }
    fra
  }

  
  Prix_swaptions_receveur_MonteCarlo <- function(T2,S2,n2,X2,Rt2,a2,sigma2,f0t2,P0t2,pas2)
  {
    #a paralleliser
    #calcul facteurs d'actualisation
    Factua<-array(1,dim=c(length(Rt2[,1]),1))
    for (incr in 1:(T2/pas2+1-1))
    {
      Factua<-Factua*(Prix_ZC((incr-1)*pas2,incr*pas2,a2,sigma2,f0t2,P0t2,pas2))
    }
    #toujours pour un notionnel de 1
    payoff_actualise<-(Valeur_swap_receveur(T2,S2,n2,X2,a2,sigma2,f0t2,P0t2,pas2)+abs(Valeur_swap_receveur(T2,S2,n2,X2,a2,sigma2,f0t2,P0t2,pas2)))/2*Factua
    #puis moyenner sur toutes les simulations
    return(mean(payoff_actualise))

  }

  Prix_swaptions_payeur_MonteCarlo <- function(T2,S2,n2,X2,Rt2,a2,sigma2,f0t2,P0t2,pas2)
  {
    #a paralleliser
    #calcul facteurs d'actualisation
    Factua<-array(1,dim=c(length(Rt2[,1]),1))
    for (incr in 1:(T2/pas2+1-1))
    {
      Factua<-Factua*(Prix_ZC((incr-1)*pas2,incr*pas2,a2,sigma2,f0t2,P0t2,pas2))
    }
    #toujours pour un notionnel de 1
    payoff_actualise<-(Valeur_swap_payeur(T2,S2,n2,X2,a2,sigma2,f0t2,P0t2,pas2)+abs(Valeur_swap_payeur(T2,S2,n2,X2,a2,sigma2,f0t2,P0t2,pas2)))/2*Factua
    #puis moyenner sur toutes les simulations
    return(mean(payoff_actualise))
    
  }
  
  ###############################################
  # Prix_swaptions_receveur_MonteCarlo(0,Tdeb,S,n,X,Rt,a,sigma,f0t,P0t,pas) #scalaire
  return(Prix_swaptions_payeur_MonteCarlo(Tdeb,S,n,X,Rt,a,sigma,f0t,P0t,pas))

  #libere la mémoire vive inutile
  rm(list=c('Rt')) #TBD
  #rm(list=ls())
  gc()
  
} #fin fonction
  
