###############
# fct: ActionBS
###############
#fonction qui genere les tirages type Black & Scholes pour les actions 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 27/10/2017 par Maxime Louardi
# modifiée le: 26/12/2017 par Sébastien Gallet
#
# Version : 1.3 (formules vectorisées)
#
# variables d entree#######################
# Param_action = fichier Rdata contenant les paramètres calibrés de la fonction de Black & Scholes
#               3 paramètres:
#                             MoyenneActions: TrSR[,k]  #taux sans risque de l'année
#                             VolatiliteActions: sigma
#                             Rendement action à t=0: Actiont
# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
##################


ActionBS <- function(Param_action,TrSR,Mat_resid_name,nom_sortie,pas_t,reptravail)
  { #debut fonction
  # Param_action<-"Param_action.Rda"
  # TrSR<-"Tr-Rt.Rda"
  # Mat_resid_name<-"Epsilon.Rda"
  # nom_sortie<-"Tr-action"
  # pas_t<-0.5
  # reptravail<-reptravail

# Chargement des fonctions utilisées
#source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Blackscholes.R", sep=""))

# Chargement de la matrice des taux sans risque TrSR : nom Rt
load(paste0(reptravail,"/R1 MEFCUBE/R1 IN/",TrSR) ) #rendement cumulé sur la période
load(paste0(reptravail,"/R1 MEFCUBE/R1 IN/","rt.Rda") ) #taux court instantanne
  
#chargement du cube des residus correles
load(paste(reptravail,"/R2 CUBE/R2 IN/",Mat_resid_name, sep="") )
#definition de la taille des matrices
N<-dim(Mat_res) [2]
Tps<-dim(Mat_res) [3]

# Chargement des paramètres calibrés
load(paste(reptravail,"/R2 CUBE/R2 IN/",Param_action, sep="") ) #parametres de calibrage de la fonction B&S pour actions
sigmaBS<-sigma
load(paste(reptravail,"/R2 CUBE/R2 IN/","a_sigma_V3.Rda", sep="") ) 
sigmaTC<-sigma

#Initialisation des actifs pour le calcul du rendement des actions
RdtActions<-matrix(0,nrow=N,ncol=Tps)
RdtActionsP<-matrix(0,nrow=N,ncol=Tps)
RdtActionsDvd<-matrix(0,nrow=N,ncol=Tps)

#Simulations des actifs actions pour toutes les périodes de projection

  #Simulations
# solution 1: classique, mais necessite des pas fins
  #RdtActions[,2:Tps]<-Blackscholes(rt[,2:(Tps)]+sigma^2/2,sigma,Mat_res[5,,2:Tps],pas_t)  #1 Tx_Inflation	2 Rdt_Immobilier	3 Tx_reel_long	4 Tx_reel_court	5 Rdt_exces_actions
# solution 2: on prend la moyenne sur le pas temps comme rt
  #RdtActions[,2:Tps]<-Blackscholes(Rt[,2:(Tps)]/pas_t+sigma^2/2,sigma,Mat_res[5,,2:Tps],pas_t)  #1 Tx_Inflation	2 Rdt_Immobilier	3 Tx_reel_long	4 Tx_reel_court	5 Rdt_exces_actions
load(paste0(reptravail,"/R4 CALIBRAGE/R4 OUT/","Prix_P0t_interp_",sc,".Rda")) 
load(paste0(reptravail,"/R4 CALIBRAGE/R4 OUT/","f0t_liss_",sc,".Rda")) 
source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_K_HullWhite.R",sep=""))
source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_L_HullWhite.R",sep=""))

alphaTC<--log(P0t_interp[2:Tps]/P0t_interp[1:(Tps-1)])+K(pas_t,a)^2/2*L(1:(Tps-1),sigmaTC,a)-K(pas_t,a)*(f0t_liss[1:(Tps-1)]-rt[,1:(Tps-1)])
betaTC<-K(pas_t,a)*L(1:(Tps-1),sigmaTC,a)^0.5
betaBS<-sigmaBS*pas_t^0.5
rho=0 # on ne considère pas la correlation pour l'instant. A modifier!!!!!
muAct<-(alphaTC-(betaBS^2+betaTC^2)/2+betaBS*K(pas_t,a)*L(1:(Tps-1),sigmaTC,a)^0.5*rho)/pas_t+sigmaBS^2/2
#muAct<-Rt[,2:Tps]+sigmaBS^2/2
RdtActions[,2:Tps]<-((muAct-sigmaBS^2/2+PMR[,2:Tps]*sigmaBS)*pas_t+betaBS*Mat_res[5,,2:Tps])


  RdtActionsDvd[,2:Tps]<-log(1+dvd)*pas_t #conversion du taux annuel en continu puis reduction au pas_t
  RdtActionsP[,]<-RdtActions[,]-RdtActionsDvd[,]

print("fin de calcul des 3 tranches Actions")
flush.console()
  
#savegarde au format Rdata des matrices de rendements actions, dividendes et capitalisation(prix)
save(RdtActions,RdtActionsP,RdtActionsDvd, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie,".Rda",sep=""))

print("enregistrement des 3 tranches Actions ds /R1 MEFCUBE/R1 IN/")
flush.console()

rm(list=c('RdtActions','RdtActionsP','RdtActionsDvd','rt','sigma','Mat_res','dvd'))
#rm(list=ls())
gc()

} #fin fonction