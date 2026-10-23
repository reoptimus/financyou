##############################
#
#### visualisation GSE++ ####
#
# cree le 10/01/2020
# permet la visualisation de la rentabilit? des actifs apres impots/taxes
load("D:/R_Financyou/GSE+/R1 CUBE++/R1 OUT/GSE++_20200717.Rda")
Tp=1 #anne de debut de l'investissement


for (prod_epar in 1:length(tableau_invest$Tr_GSE_Prix)) {
  
  Ra_an<-GSE_plac_taxes_cuml[,,,prod_epar]
  ra_an<-GSE_plac_taxes_an[,,,prod_epar]
  R3D_an<-GSE_plac_taxes[,,,prod_epar,3]
  comparatif<-R3D_an[,Tp,]
  
  plot((1:dim(Ra_an[,,])[3]),colQuantiles(Ra_an[,Tp,(1:dim(Ra_an[,,])[3])],prob=0.5),type="l",ylim=c(0.95,1.1),lwd=2,lty=5,pch=5,col="red",main=paste0("Rdt A ",tableau_invest[prod_epar,2]),xlab="Ann?e de projection",ylab="Rdt moy et quant ? 10 % et ? 90 %")
  lines((1:dim(Ra_an[,,])[3]),rep(1,dim(Ra_an[,,])[3]),type="l",col="black")
  lines((1:dim(Ra_an[,,])[3]),colQuantiles(Ra_an[,Tp,(1:dim(Ra_an[,,])[3])],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
  lines((1:dim(Ra_an[,,])[3]),colQuantiles(Ra_an[,Tp,(1:dim(Ra_an[,,])[3])],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
  lines((1:dim(Ra_an[,,])[3]),mat_EV[prod_epar,,1],type="l",lwd=1,lty=2,pch=10,col="black")
  lines((1:dim(comparatif[,])[2]),colQuantiles(comparatif[,(1:dim(comparatif[,])[2])],prob=0.5),type="l",lwd=2,lty=5,pch=5,col="blue")
  lines((1:dim(comparatif[,])[2]),colQuantiles(comparatif[,(1:dim(comparatif[,])[2])],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="blue")
  lines((1:dim(comparatif[,])[2]),colQuantiles(comparatif[,(1:dim(comparatif[,])[2])],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="blue")
  
  plot((1:dim(ra_an[,,])[3]),colQuantiles(ra_an[,Tp,(1:dim(ra_an[,,])[3])],prob=0.5),type="l",ylim=c(0.90,1.1),lwd=2,lty=5,pch=5,col="red",main=paste0("Rdt a ",tableau_invest[prod_epar,2]),xlab="Ann?e de projection",ylab="Rdt moy et quant ? 10 % et ? 90 %")
  lines((1:dim(ra_an[,,])[3]),colQuantiles(ra_an[,Tp,(1:dim(ra_an[,,])[3])],prob=0.9),type="l",lwd=1,lty=5,pch=5,col="red")
  lines((1:dim(ra_an[,,])[3]),colQuantiles(ra_an[,Tp,(1:dim(ra_an[,,])[3])],prob=0.1),type="l",lwd=1,lty=5,pch=5,col="red")
  
} #fin de la boucle sur les produits d'epargnes

H=5
plot(mat_EV[,H,2],mat_EV[,H,1],type="p",xlim=c(0,max(mat_EV[,H,2])),ylim=c(0.97,max(mat_EV[,H,1])),col="red")
points(0,0,pch=19,col="black")
for (i in 1:length(tableau_invest$Tr_GSE_Prix)) {
  text(mat_EV[i,H,2],mat_EV[i,H,1], as.character(i), cex=1, pos=1 , col="blue")
}
list<-seq(0,1,0.1)
lines(list,rep(1,length(list)))
