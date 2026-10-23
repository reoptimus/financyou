#####################################
# fct: Visualisation de la martingalité des matrices
###############
#
# crée le: 06/08/2018 par Sébastien Gallet
#
# Version : 1
#####################################

#Chargement du package utilisé
require(matrixStats)

#données à traiter
chemin<-"Z:/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts/R2 CUBE/R2 OUT"
setwd(chemin)

# Chargement des fonctions utilisées: cumul des rendements
source("../R2 Fonctions locale/F_Rdtcumul.R")

#Deflateur<-cube[,,1]

#chargement de la matrice à tester qui utilise Rt
Mat_test<-RdtImmo #cube[,,2]

##################################################################
#calcul des rendements cumulés

CumulMatTest<-Rdtcumul(Mat_test)

#calcul de l'espérance martingale: par le deflateur
#CumulMat_mart<-exp(CumulMatTest)*Deflateur

#calcul non-cumulé avec Rt à 2%  ( a effacer )
#Rt<-array(0.02,dim=c(4000,120))
Mat_mart<-exp(Mat_test)/exp(Rt)

#calcul cumulé avec Rt à 2%  ( a effacer )
#Rt<-array(0.02,dim=c(4000,120))
CumulMat_mart<-exp(CumulMatTest)/exp(Rdtcumul(Rt))


#########################################
# Matrice visualisée
RdtCumul<-Mat_mart#CumulMat_mart
#########################################
nbannees<-dim(RdtCumul) [2]

# Graphique martingale non-cumules immo
plot((1:nbannees),apply(RdtCumul[,(1:nbannees)],2,mean),type="l",ylim=c(0.5,1.5),lwd=2,lty=5,pch=5,col="gray",main="Martingale non-cumul",xlab="Année de projection",ylab="Rdt conti cumul med & quant 10 % 90 %")
lines((1:nbannees),apply(RdtCumul[,1:(nbannees)],2,mean),type="l",lwd=2,lty=5,pch=5,col="Black")
for (i in 1:4) {
  lines((1:nbannees),RdtCumul[i,(1:nbannees)],type="l",lwd=1,lty=5,pch=5,col=i)
}
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.5),type="l",lwd=1,lty=1,pch=5,col="red")

#########################################
# Matrice visualisée
RdtCumul<-CumulMat_mart
#########################################
nbannees<-dim(RdtCumul) [2]
# Graphique martingale cumules immo
plot((1:nbannees),apply(RdtCumul[,(1:nbannees)],2,mean),type="l",ylim=c(0,2),lwd=2,lty=5,pch=5,col="gray",main="Martingale cumul",xlab="Année de projection",ylab="Rdt conti cumul med & quant 10 % 90 %")
lines((1:nbannees),apply(RdtCumul[,1:(nbannees)],2,mean),type="l",lwd=2,lty=5,pch=5,col="Black")
for (i in 1:20) {
  lines((1:nbannees),RdtCumul[i,(1:nbannees)],type="l",lwd=1,lty=5,pch=5,col=i)
}
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
lines((1:nbannees),colQuantiles(RdtCumul[,1:(nbannees)],prob=0.5),type="l",lwd=1,lty=1,pch=5,col="red")


