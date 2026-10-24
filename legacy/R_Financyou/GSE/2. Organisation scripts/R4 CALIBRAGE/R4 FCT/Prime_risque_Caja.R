# prime de risque lambda(t)
#
# diffusion de la prime de risque selon l'étude
# de Planchet et Caja sur le model de Ahmad et Wilmott [2006]
#
# dLam=(p(r)+Lam*q(r))dt + q(r) dWt

PMR_func<-function (pas_t,temp,N,reptravail,nom_sortie,pas_interne){
  # reptravail<-"E:/YAALI/package R/6. ESG_V2/2. Organisation scripts"
library(caTools)

#donnees entree exemple
 # pas_t<-0.5 #pas de temp du GSE
 # temp<-40 #nb annees de projection
 # N<-1000 #nb de scenario
 # nom_sortie<-"PMR"
 # setwd("E:/")
 # reptravail<-getwd()
 # reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")

  
  ################################################
  # paramètre interne de lissage de la PMR sur x année
  #pas_interne<-0.5 #pas interne de lissage pour la PMR
  ################################################

# données de calibrage
Lamax=20.43
l=2.8234
m=0.2984
Beta=0.5968/2
Lamoy=exp(3.1149)
c=0.2217
dt=1/257

# initialisation
Lambda0<-array(0,dim=c(N,1))
nb_pas=temp/dt
Lambda<-array(0, dim=c(N,nb_pas))
Lambda[,1]<-Lambda0

# boucle sur le pas de temps i=2
for (i in 2:nb_pas) {
Lam<-Lambda[,i-1]
q=l*(Lamax-Lam)^m
p = l^2*(Lamax-Lam)^(2*m-1)*(-m+0.5+1/(2*c^2)*log(((Lamax-Lam)/Lamoy)))
dLam=-((p+Lam*q)*dt+q*dt^0.5*array(rnorm(N,0,1),dim=c(N,1)))
Lambda[,i]<-Lambda[,i-1]+dLam
}
#plot(apply(Lambda,2,mean),type="l")

# donnes de sortie

PMR_interne<-array(0,dim=c(N,length(Lambda[1,seq(1,nb_pas,257*pas_interne)])))

for (i in 1:N) {
PMR_interne[i,]<-runmean(Lambda[i,],257*pas_interne)[seq(1,nb_pas,257*pas_interne)] # moyenne sur la periode
}
#PMR_interne[,]<-Lambda[,seq(1,nb_pas,257*pas_interne)] # derniere valeur de la periode


#remise au pas de temps demandé par interpolation
nb_pas_int<-dim(PMR_interne)[2]
nb_interp<-pas_interne/pas_t

PMR<-array(0,dim=c(N,(temp/pas_t)))
x <- 1:nb_pas_int

for (i in 1:N){
  y <- PMR_interne[i,]
  PMR[i,]<-approx(x, y,n=(nb_interp*nb_pas_int))$y 
}

par(mar=c(4,4,3,1))
plot(apply(PMR,2,mean),type="l",col="black",ylim=c(-4,5),main="PMR")
lines(apply(PMR,2,quantile,probs=c(0.005)),type="l",col="red")
lines(apply(PMR,2,quantile,probs=c(0.995)),type="l",col="blue")
for (i in 1:3) {
  lines(PMR[i,],type="l")
}

# enregistrement dans les données d entree du calcul CUBE
save(PMR,file=paste(reptravail,"/R2 CUBE/R2 IN/",nom_sortie,".Rda" ,sep=""))

}