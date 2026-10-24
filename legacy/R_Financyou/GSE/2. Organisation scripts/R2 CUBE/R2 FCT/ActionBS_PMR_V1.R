###############
# fct: ActionBS_PMR
###############
#fonction qui genere les tirages type Black & Scholes pour les actions avec PMR historique
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 27/10/2017 par Maxime Louardi
# modifiée le: 28/04/2019 par Sébastien Gallet
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

 
# Fonction pour generation nombre aletoire correle
ActionBS <- function(Param_action,TrSR,Mat_resid_name,nom_sortie,pas_t,reptravail)
  { #debut fonction

# Chargement de la matrice des taux sans risque TrSR : nom Rt
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/",TrSR, sep="") )
  
#chargement du cube des residus correles
load(paste(reptravail,"/R2 CUBE/R2 IN/",Mat_resid_name, sep="") )
#definition de la taille des matrices
N<-dim(Mat_res) [2]
Tps<-dim(Mat_res) [3]

# Chargement des paramètres calibrés
load(paste(reptravail,"/R2 CUBE/R2 IN/",Param_action, sep="") ) #parametres de calibrage de la fonction B&S pour actions

#Initialisation des actifs pour le calcul du rendement des actions
RdtActions<-matrix(0,nrow=N,ncol=Tps)
RdtActionsP<-matrix(0,nrow=N,ncol=Tps)
RdtActionsDvd<-matrix(0,nrow=N,ncol=Tps)

#Simulations des actifs actions pour toutes les périodes de projection

  #Simulations
  RdtActions[,2:Tps]<-(Rt[,2:(Tps)]-sigma^2/2+PMR[,2:Tps]*sigma)*pas_t+sigma*(pas_t^0.5)*Mat_res[5,,2:Tps]
  RdtActionsDvd[,2:Tps]<-log(1+dvd)*pas_t #conversion du taux annuel en continu puis reduction au pas_t
  RdtActionsP[,]<-RdtActions[,]-RdtActionsDvd[,]

print("fin de calcul des 3 tranches Actions")
flush.console()
  
#savegarde au format Rdata des matrices de rendements actions, dividendes et capitalisation(prix)
save(RdtActions,RdtActionsP,RdtActionsDvd, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie,".Rda",sep=""))

print("enregistrement des 3 tranches Actions ds /R1 MEFCUBE/R1 IN/")
flush.console()

rm(list=c('RdtActions','RdtActionsP','RdtActionsDvd','Rt','sigma','Mat_res','dvd'))
#rm(list=ls())
gc()

} #fin fonction