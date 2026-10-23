
###############
#Script qui genere le Cube deflaté pour test de martingalité 
#
# crée le: 22/12/2017 par Sébastien Gallet
# modifiée le: 09/02/2018 par Sébastien Gallet
#
# Version : 2
#
# variables d entree#######################
# ESG.Rda = Matrice N*T*Nb actifs
# nom_sortie = ESG-martingal.Rda
###########################################

nomESG<-"ESG.Rda"
nomsortie<-"ESG-martingal"
nomTauxSR<-"Tr-Rt2%.Rda"

reptravail<-"Z:/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts"
setwd(reptravail)
# Chargement de la matrice cube des sorties ESG
load(paste(reptravail,"/R1 MEFCUBE/R1 OUT/",nomESG, sep="") )

# Variables globales
N<-dim(cube[,,])[1]
T<-dim(cube[,,])[2]
NbAct<-dim(cube[,,])[3]

# Chargement des fonctions utilisées: cumul des rendements
source("./R1 MEFCUBE/R1 Fonctions locale/F_Rdtcumul3D.R")
source("./R1 MEFCUBE/R1 Fonctions locale/F_Rdtcumul.R")

#calcul des rendement des actifs cumulés
CumulESG<-array(0,c(N,T,NbAct))
CumulESG<-Rdtcumul3D(cube)

#Calcul du cube [exp(sum1-T(Ract)) / exp(sum1-T(Rt))] dont on veut évaluer l'espérance

load(paste(reptravail,"/R2 CUBE/R2 IN/",nomTauxSR, sep="") )
CumulRt<- Rdtcumul(Rt)
CumulRt3D<-array(rep(CumulRt,NbAct),dim=c(N,T,NbAct))

#calcul 3D pour tous N T et tranches d'actifs simultannement
Esp_Prix_marting<-array(0,c(N,T,NbAct))
Esp_Prix_marting<-exp(CumulESG)/exp(CumulRt3D)


Esp_Prix_marting<-exp(CumulESG[,1:119,])*rep(cube[,2:120,1],dim(cube)[3])


plot(apply(Esp_Prix_marting[,,47],2,mean))

rm(list=c('N','T','NbAct','CumulESG','CumulRt3D','CumulRt','nomESG','cube','Rt'))
#rm(list=ls())
gc()

#savegarde au format Rdata de la mat de tranches cumulées martingalisées
save(Esp_Prix_marting, file=paste(reptravail,"/R1 MEFCUBE/R1 Validation/",nomsortie,".Rda",sep=""))
rm(list=c('Esp_Prix_marting','nomsortie'))
#rm(list=ls())
gc()

