#plot  des VaR du fichier indiqué

#Chargement du package utilisé
require(matrixStats)

#données à traiter
chemin<-"Z:/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts/R2 CUBE/R2 OUT"
setwd(chemin)

# Chargement des fonctions utilisées: cumul des rendements
source("../R2 Fonctions locale/F_Rdtcumul.R")


#########################################
# Matrice visualisée à modifier au besoin
RdtnonCumul<-Rt
#########################################
# Nb année pour la visualisation
nbannees<-dim(RdtnonCumul) [2]

# Graphique rendements (non-cumulés)
plot((1:nbannees),colQuantiles(RdtnonCumul[,1:(nbannees)],prob=0.5),type="l",ylim=c(-0.1,0.5),lwd=2,lty=5,pch=5,col="red",main="Rdt",xlab="Année de projection",ylab="Rdt moy et quant à 10 % et à 90 %")
lines((1:nbannees),apply(RdtnonCumul[,1:(nbannees)],2,mean),type="l",lwd=2,lty=5,pch=5,col="Black")
lines((1:nbannees),colQuantiles(RdtnonCumul[,1:(nbannees)],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtnonCumul[,1:(nbannees)],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
for (i in 1:3) {
  lines((1:nbannees),RdtnonCumul[i,(1:nbannees)],type="l",lwd=0.5,lty=5,pch=5,col=i)
}

#calcul des rendements cumulés
RdtCumul<-matrix(0,nrow=dim(RdtnonCumul)[1],ncol=dim(RdtnonCumul)[2])
RdtCumul<-Rdtcumul(RdtnonCumul)
#RdtCumul<-exp(RdtCumul)*RdtDefl

# Graphique rendements cumules immo
plot((1:nbannees),apply(RdtCumul[,(1:nbannees)],2,mean),type="l",ylim=c(-0.1,20),lwd=2,lty=5,pch=5,col="gray",main="Rdt continus cumules",xlab="Année de projection",ylab="Rdt conti cumul med & quant 10 % 90 %")
lines((1:nbannees),apply(RdtCumul[,1:(nbannees)],2,mean),type="l",lwd=2,lty=5,pch=5,col="Black")
for (i in 1:20) {
  lines((1:nbannees),RdtCumul[i,(1:nbannees)],type="l",lwd=1,lty=5,pch=5,col=i)
}
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.5),type="l",lwd=1,lty=1,pch=5,col="red")
