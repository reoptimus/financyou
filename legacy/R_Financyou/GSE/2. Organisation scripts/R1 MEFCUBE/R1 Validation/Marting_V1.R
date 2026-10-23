
###############
#Script qui genere le Cube deflaté pour test de martingalité 
#
# crée le: 22/12/2017 par Sébastien Gallet
# modifiée le: 22/12/2017 par Sébastien Gallet
#
# Version : 1
#
# variables d entree#######################
# ESG.Rda = Matrice N*T*Nb actifs
# nom_sortie = ESG-martingal.Rda
###########################################

nomESG<-"ESG.Rda"
nomsortie<-"ESG-martingal"

reptravail<-"Z:/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts/R1 MEFCUBE"
setwd(reptravail)

# Chargement de la matrice cube des sorties ESG
load(paste(reptravail,"/R1 OUT/",nomESG, sep="") )

# Variables globales
N<-dim(cube[,,])[1]
T<-dim(cube[,,])[2]
NbAct<-dim(cube[,,])[3]

# Chargement des fonctions utilisées: cumul des rendements
source("./R1 Fonctions locale/F_Rdtcumul3D.R")

#calcul des rendement des actifs cumulés
CumulESG<-array(0,c(N,T,NbAct))
CumulESG<-Rdtcumul3D(cube)

#Calcul du cube deflaté pour des rendements continus
PrixDefl<- array(0,dim=c(N,T,NbAct))
   #Rappel:la matrice des déflateurs est cube[,,1]
   PrixDefl[,,1]<-cube[,,1]
   for (i in 2:NbAct){
   PrixDefl[,,i]<-cube[,,1]*exp(CumulESG[,,i])
   }

#savegarde au format Rdata de la mat de residus correles
save(PrixDefl, file=paste("./R1 Validation/",nomsortie,".Rda",sep=""))

rm(list=c('N','T','NbAct','CumulESG','PrixDefl','nomESG','nomsortie','i','cube'))
#rm(list=ls())
gc()
