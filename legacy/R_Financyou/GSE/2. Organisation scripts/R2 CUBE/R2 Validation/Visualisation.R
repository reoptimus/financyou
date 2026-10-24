#plot  des VaR du fichier indiqué

#Chargement du package utilisé
require(matrixStats)

#données à traiter
chemin<-"//Intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG_V2/2. Organisation scripts/R2 CUBE/R2 OUT"
#\\Intra\partages\UA2771_Data\3_ST_top-down\3.2_En\6. ESG_V2\2. Organisation scripts\R2 CUBE\R2 OUT
setwd(chemin)

fichier<-"Tr-action.Rda" 
fichier<-"Tr-immo-SR.Rda"
fichier<-"Tr-Rt.Rda"
load(paste(chemin,"/",fichier,sep=""))

#choisir la matrice etudiee
RdtMat<-RdtActions
RdtMat<-RdtImmo
RdtMat<-Rt
RdtMat<-Defl

# Chargement des fonctions utilisées: cumul des rendements
source("../R2 Fonctions locale/F_Rdtcumul.R")

#calcul des rendements cumulés
N<-length(RdtMat[,1])
nbannees<-length(RdtMat[1,])
CumulRdtMat<-matrix(0,nrow=N,ncol=nbannees)
CumulRdtMat<-Rdtcumul(RdtMat)

RdtMat<-exp(RdtMat)-1
CumulRdtMat<-exp(CumulRdtMat)-1

# Graphique rendements (non-cumulés)
plot((1:nbannees),colQuantiles(RdtMat[,1:(nbannees)],prob=0.5),type="l",ylim=c(0,0.3),lwd=2,lty=5,pch=5,col="red",main="Rdt immo Orn-Uhl",xlab="Année de projection",ylab="Rdt moy et quant à 10 % et à 90 %")
lines((1:nbannees),colQuantiles(RdtMat[,1:(nbannees)],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtMat[,1:(nbannees)],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")

for (i in 1:10) {
  lines((1:nbannees),RdtMat[i,(1:nbannees)],type="l",lwd=1,lty=5,pch=5,col="grey")
}

# Graphique rendements cumules immo
plot((1:nbannees),apply(CumulRdtMat[,(1:nbannees)],2,mean),type="l",ylim=c(-0.1,10),lwd=2,lty=5,pch=5,col="red",main="Rdt continus cumules immo Orn-Uhl",xlab="Année de projection",ylab="Rdt conti cumul med & quant 10 % 90 %")
for (i in 1:10) {
  lines((1:nbannees),CumulRdtMat[i,(1:nbannees)],type="l",lwd=1,lty=5,pch=5,col="grey")
}
lines((1:nbannees),colQuantiles(CumulRdtMat[,1:(nbannees)],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(CumulRdtMat[,1:(nbannees)],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(CumulRdtMat[,1:(nbannees)],prob=0.5),type="l",lwd=1,lty=1,pch=5,col="red")

# Graphique rendements cumules Actions
plot((1:nbannees),apply(CumulRdtActions[,(1:nbannees)],2,mean),type="l",ylim=c(-0.9,8),lwd=2,lty=5,pch=5,col="red",main="Rdt continus cumules actions B&S",xlab="Année de projection",ylab="Rdt conti cumul med & quant 10 % 90 %")
for (i in 1:100) {
  lines((1:nbannees),CumulRdtActions[i,(1:nbannees)],type="l",lwd=1,lty=5,pch=5,col="grey")
}
lines((1:nbannees),colQuantiles(CumulRdtActions[,1:(nbannees)],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(CumulRdtActions[,1:(nbannees)],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(CumulRdtActions[,1:(nbannees)],prob=0.5),type="l",lwd=1,lty=1,pch=5,col="red")

rm(list=ls())
gc()
