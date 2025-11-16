###############
# fct: Calib_ActionBS
###############
#fonction qui genere les tirages type Black & Scholes pour les actions 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 06/06/2018 par Sébastien Gallet
# modifiée le: 
#
# Version : 1
#
# variables d entree#######################
# Param_calib_action = fichier Rdata contenant les prix du call, prix du sous-jacent, strike
# MoyenneActions: TrSR  #taux sans risque
# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie
# pas_t = le pas de temps en année utilisé (ex:1/12 pour mensuel)
#################

Calib_ActionBS <- function(TrSR,Mat_resid_name,nom_sortie,pas_t,reptravail)
  { #debut fonction

  ################
#Paramètres internes de param_calib-action à effacer
  ################

#install.packages("xlsx") 
library("xlsx")
##################

# # a effacer 
reptravail<-'\\\\intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG_V2/2. Organisation scripts/'
TrSR<-'Tr-Rt.Rda'
Mat_resid_name<-'Epsilon.Rda'
Param_calib_action<-"Call_V1.xlsx"
pas_t<-0.5
nom_sortie<-"Param_action.Rda"

#chargement des données des calls
Mat_call<-read.xlsx(file=paste(reptravail,"R4 CALIBRAGE/R4 IN/",Param_calib_action, sep=""),1, header=FALSE)
nb_call<-length(Mat_call[1,])-1

#mise en forme des données
prix_call<- as.numeric(Mat_call[4,2:(nb_call+1)]) #calcul a partir du site iotafinance.com sans div
S<-as.numeric(Mat_call[2,2:(nb_call+1)])
K<-as.numeric(Mat_call[3,2:(nb_call+1)])
Maturite<-as.numeric(round(Mat_call[1,2:(nb_call+1)]/pas_t,0)) #on ne conserve que les colonnes qui corresponde aux maturités des options
Ponderation<-as.numeric(Mat_call[6,2:(nb_call+1)])

# Chargement des fonctions utilisées
source(paste(reptravail,"R2 CUBE/R2 Fonctions locale/F_Blackscholes.R",sep=""))
source(paste(reptravail,"R2 CUBE/R2 Fonctions locale/F_Rdtcumul.R",sep=""))

# Chargement de la matrice des taux sans risque TrSR : nom Rt
load(paste(reptravail,"R2 CUBE/R2 IN/",TrSR, sep="") )
  
#chargement du cube des residus correles
load(paste(reptravail,"R2 CUBE/R2 IN/",Mat_resid_name, sep="") )

#definition de la taille des matrices
N<-dim(Mat_res) [2]
T<-dim(Mat_res) [3]
Nb_slices<-dim(Mat_res) [1]
Maturite_max<-max(Maturite)

#Initialisation des variables
RdtActions<-matrix(0,nrow=N,ncol=T)
RdtActionsP<-matrix(0,nrow=N,ncol=T)
RdtActionsDvd<-matrix(0,nrow=N,ncol=T)
CumulRdtActions<-matrix(0,nrow=N,ncol=T)
Prix_call_list<-matrix(0,nrow=N,ncol=max(Maturite)) #initialisation
Prix_call<-matrix(0,nrow=Nb_slices,ncol=length(Maturite))

# initialisation de l'optimisation de sigma
sigma<-0.4 #point de depart arbitraire
ecart_quad_final<-100000000 #très grand au debut
pas_sigma<-0.1
sens<-paste("Pas=",pas_sigma,sep="")
nb_pas_raf=7
nb_opt=0

#########################% Boucle d'optimisation
while (nb_opt<nb_pas_raf){ # nb_opt est le nombre de rafinement du pas avant l'arret

  for (i in 1:Nb_slices){# pour une tranche de variable aléa

  #Simulations des actifs actions pour toutes les périodes de projection
    RdtActions[,]<-Blackscholes(Rt[,],sigma,Mat_res[i,,],pas_t)  #1 Tx_Inflation	2 Rdt_Immobilier	3 Tx_reel_long	4 Tx_reel_court	5 Rdt_exces_actions
    #RdtActionsDvd[,]<-dvd
    #RdtActionsP[,]<-RdtActions[,]-RdtActionsDvd[,]
    
  #calcul du prix d'un call (sans div)
    CumulRdtActions<-Rdtcumul(RdtActions)
    CumulTsr<-Rdtcumul(Rt)
    Prix_call_list<-t(S*t(exp(CumulRdtActions[,Maturite]))) #calcul de S(T)
    Prix_call_list<-t(Prix_call_list)
    Prix_call_list<-t(ifelse(Prix_call_list > K,Prix_call_list-K,0))  #mise à zero de option perdante et calcul S(T)-K
    Prix_call_list<-Prix_call_list*exp(-t(t(CumulTsr[,Maturite]))) #actualisation des pay-offs
    Prix_call[i,]<-apply( Prix_call_list,2,mean)  #calcul de la moyenne
    
  }#fin de boucle sur les slices de tirages alea

#critère d'optimisation en %
opt<-apply(t((t(Prix_call)-prix_call)/prix_call),2,mean) #ecart moyen en % (du prix) par call entre prix observé et le calcul sur les 5 tirages aléatoires
opt<-opt*Ponderation #ponderation des options dans le critère d'optimisation

#ecart quad en % pour chaque call (attention: une seule vol pour tous les call/maturité)
ecart_quad<-(sum(opt^2))^0.5

#test pour la boucle d'optimisation
if (ecart_quad<ecart_quad_final) {
  ecart_quad_final<-ecart_quad
  
} else { #ecart quad n'est pas amélioré
    #remettre sigma dans sa derniere position
      if (sens[length(sens)]=="+") {
        sigma<-sigma-pas_sigma  
      }else{
        sigma<-sigma+pas_sigma  
      }
    sens[length(sens)]="Pas/2"
    pas_sigma<-pas_sigma/2 #raffinement du pas
    nb_opt=nb_opt+1 #l'increment du nombre de boucle, on veut nb_pas_raf fois le rafinement du pas
} #fin du test pour voir si il y a amelioration du resultat

#test pour modifier le sens de pas_sigma (utilisation de la croissance des prix d'un call vs. la vol)
if (sum(opt) < 0){ #si le total pondéré des erreurs en % par option est négatif
  #cela implique que le prix modélisé < prix observé -> il faut augmenter la Vol
  sigma<-sigma+pas_sigma
  sens<-cbind(sens,"+") #marqueur de la direction prise
  } else {
    sigma<-sigma-pas_sigma
    sens<-cbind(sens,"-") #marqueur de la direction prise
  }
} 
####################fin de la boucle For d'optimisation
# affichage du chemin d'optimisation est du sigma optimisé
sens
sigma

#enregistre au format Param_action.Rda
Actiont<-0.03
dvd<-0.02
save(sigma,Actiont,dvd,file=paste(reptravail,"/R4 CALIBRAGE/R4 OUT/",nom_sortie,sep=""))

#efface les variables utilisées pour les calculs
rm(list=c('nb_pas_raf','opt','ecart_quad','ecart_quad_final','Nb_slices','Maturite_max','CumulRdtActions','RdtActions','RdtActionsP','RdtActionsDvd','Rt','sigma','Mat_res','dvd'))
#rm(list=ls())
gc()

} #fin fonction