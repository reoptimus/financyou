###############
# fct: Deflator
###############
#fonction qui genere les deflateur à partir des taux sans risques cumulés
#
#
# crée le: 22/12/2017 par Sébastien Gallet
# modifiée le: 16/08/2018 par Sébastien Gallet
#
# Version : 2 ajout de pas_t avec Rdtcumul(Rt*pas_t)
#
# variables d entree#######################
# Tr-Rt.Rda = Matrice N*T des taux sans risques
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

Deflator <- function(TrSR,nom_sortie,pas_t,reptravail)
  { #debut fonction

# Chargement des fonctions utilisées: cumul des rendements
source(paste(reptravail,"/R2 Fonctions locale/F_Rdtcumul.R",sep=""))

# Chargement de la matrice des taux sans risque TrSR : nom Rt
load(paste(reptravail,"/R2 IN/",TrSR, sep="") ) #variable Rt une fois chargée
#definition de la taille des matrices
N<-dim(Rt) [1]
Tf<-dim(Rt) [2]

##################################
# Formation des déflateurs à partir des taux sans risques continu
########################

#calcul des taux sans risque cumulés
CumulTrSR<-matrix(0,nrow=N,ncol=Tf)
CumulTrSR<-Rdtcumul(Rt*pas_t)

#Calcul du déflateur pour toutes les périodes de projection en taux continus
RdtDefl<-exp(-CumulTrSR)

#savegarde au format Rdata de la matrice des déflateurs
save(RdtDefl, file=paste("./R2 OUT/",nom_sortie,".Rda",sep=""))

rm(list=c('RdtDefl','CumulTrSR'))
#rm(list=ls())
gc()

} #fin fonction