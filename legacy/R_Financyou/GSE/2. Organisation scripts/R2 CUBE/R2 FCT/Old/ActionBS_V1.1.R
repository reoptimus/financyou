###############
# fct: ActionBS
###############
#fonction qui genere les tirages type Black & Scholes pour les actions 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 27/10/2017 par Maxime Louardi
# modifiée le: 27/10/2017 par Maxime Louardi
#
# Version : 1.1
#
# variables d entree#######################
# Param_action = fichier Rdata contenant les paramètres calibrés de la fonction de Black & Scholes
#               3 paramètres:
#                             MoyenneActions: mu
#                             VolatiliteActions: sigma
#                             Rendement action à t=0: Actiont
# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
##################
#    dvd<-TrSR[,k-1]    ##### ici les dividendes annuels sont égaux au taux sans risque de l'année précédente
##################
###########################################
 
# Fonction pour generation nombre aletoire correle
ActionBS <- function(param_action,TrSR,Mat_resid_name,nom_sortie)
  { #debut fonction

# Chargement des fonctions utilisées
source("./R2 Fonctions locale/F_Blackscholes.R")

# Chargement de la matrice des taux sans risque TrSR
load(paste(reptravail,"/R2 IN/",TrSR, sep="") )
  
#chargement du cube des residus correles
load(paste(reptravail,"/R2 IN/",Mat_resid_name, sep="") )

# Chargement des paramètres calibrés
load(paste(reptravail,"/R2 IN/",param_action, sep="") ) #parametres de calibrage de la fonction B&S pour actions

#Initialisation des actifs pour le calcul du rendement des actions
RdtActions<-matrix(0,nrow=N,ncol=T)
RdtActions[,1]<-Actiont

RdtActionsP<-matrix(0,nrow=N,ncol=T)
RdtActionsDvd<-matrix(0,nrow=N,ncol=T)

#Simulations des actifs pour les actions pour toutes les périodes de projection et réinitialisation #des paramètres
for(k in 2:T){
  #Simulations
  RdtActions[,k]<-Blackscholes(TrSR[,k],sigma,Mat_res[4,,k]) # 4 = action depend de la matrice de correlation
  RdtActionsDvd[,k]<-TrSR[,k-1]
  RdtActionsP[,k]<-Blackscholes(mu,sigma,Mat_res[4,,k])-RdtActionsDvd[,k]
  #Réinitialisation
  #Actiont<-RdtActions[,k] #pas necessaire ici
}

#savegarde au format Rdata de la mat de residus correles
save(RdtActions,RdtActionsP,RdtActionsDvd, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))


rm(list=c('RdtActions','RdtActionsP','RdtActionsDvd','mu','sigma','Actiont','Mat_res'))
#rm(list=ls())
gc()

} #fin fonction