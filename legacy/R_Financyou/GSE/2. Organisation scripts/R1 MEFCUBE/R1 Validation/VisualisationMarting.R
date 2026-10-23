#Visualisation du cube ESG cumulé et multiplié par le Deflator
# La variable est alors ESG-martingal.Rda

#Chargement du package utilisé
require(matrixStats)

#données à traiter
chemin<-"Z:/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts/R1 MEFCUBE/R1 Validation"
fichier<-"ESG-martingal.Rda"   #le nom de la variable est RdtDefl
load(paste(chemin,"/",fichier,sep=""))

PrixDefl<-Esp_Prix_marting
nbannees<-dim(Esp_Prix_marting) [2]
#Choix de la tranche observée
Tr<-3

# Graphique rendements martingals
plot((1:nbannees),colQuantiles(PrixDefl[,1:(nbannees),Tr],prob=0.5),type="l",ylim=c(-0.2,3),lwd=2,lty=5,pch=5,col="red",main="Rdt martingals",xlab="Année de projection",ylab="Rdt moy et quant à 10 % et à 90 %")
lines((1:nbannees),apply(PrixDefl[,1:(nbannees),Tr],2,mean),type="l",lwd=3,lty=5,pch=5,col="Black")
lines((1:nbannees),colQuantiles(PrixDefl[,1:(nbannees),Tr],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(PrixDefl[,1:(nbannees),Tr],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
for (i in 1:30) {
  lines((1:nbannees),PrixDefl[i,(1:nbannees),Tr],type="l",lwd=1,lty=5,pch=5,col="grey")
}

#rm(list=ls())
gc()
