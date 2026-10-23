###############
# fct: ActionBS
###############
#fonction qui genere les tirages type Black & Scholes pour les actions 
#à partir des paramètres calibrés et du cube des variables aleatoires correles
#
# crée le: 27/10/2017 par Maxime Louardi
# modifiée le: 27/10/2017 par Maxime Louardi
#
# Version : 1.0
#
# variables d entree#######################
# Param_action = fichier Rdata contenant les paramètres calibrés de la fonction de Black & Scholes
#               3 paramètres:
#                             MoyenneActions: mu
#                             VolatiliteActions: sigma
#                             Rendement action à t=0: Actiont
# Mat_res = Matrice des residus correlés Epslion
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

# Fonction pour generation nombre aletoire correle
ActionBS <- function(param_action,Mat_resid_name,nom_sortie)
  { #debut fonction

# Chargement des fonctions utilisées
source("./R2 Fonctions locale/F_Blackscholes.R")

#chargement du cube des residus correles
load(paste(reptravail,"/R2 IN/",Mat_resid_name, sep="") )

# Chargement des paramètres calibrés
load(paste(reptravail,"/R2 IN/",param_action, sep="") ) #parametres de calibrage de la fonction B&S pour actions

#Initialisation des actifs pour le calcul du rendement des actions
RdtActions<-matrix(0,nrow=N,ncol=T)
RdtActions[,1]<-Actiont

#Simulations des actifs pour les actions pour toutes les périodes de projection et réinitialisation #des paramètres
for(k in 2:T){
  #Simulations
  RdtActions[,k]<-Blackscholes(mu,sigma,Mat_res[4,,k]) # 4 = action depend de la matrice de correlation
  #Réinitialisation
  #Actiont<-RdtActions[,k] #pas necessaire ici
}

#savegarde au format Rdata de la mat de residus correles
save(RdtActions, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))

rm(list=c('RdtActions','mu','sigma','Actiont','Mat_res'))
#rm(list=ls())
gc()

} #fin fonction