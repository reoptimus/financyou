#################################################
# script pour la visualisation des sorties GSE
# fait le 21/12/2019
#################################################
setwd("E:/")
reptravail<-getwd()
reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")

# matrice (N,Tp)
tranche<-Rt

# params
N<-dim(tranche[,])[1]
Tmp<-dim(tranche[,])[2]

# Chargement des fonctions utilis?es: cumul des rendements
source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rdtcumul.R",sep=""))

#calcul du cube_placement cumule deflat
CumulESGDefl<-Rdtcumul(tranche,0,"Y")
tranche<-exp(CumulESGDefl)*RdtDefl


x<-1:Tmp
max<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.317)
#mean<-apply(cube[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.5)
mean<-apply(tranche,MARGIN=2,FUN=mean)

# trac? non-cumul?
plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(0,10),
     xlab="time",ylab="Rate")
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")

#####################################
# Marting
#########
for (i in 1:length(list_actifs)) {
  nb_tr=i #deflator nb
  #list_actifs[nb_tr]
  
x<-1:length(CumulESGDefl[1,,nb_tr])
max<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.317)

# mean<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.5)
mean<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=mean)

# trac
plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(0,2),
     xlab="time",ylab="rates",main=paste("deflated agg returns ",list_actifs[nb_tr],sep=""),cex.main=0.8)
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")
# legend("topleft", inset=.01, title="Qantiles",
#        c(expression(3*sigma),expression(2*sigma),expression(sigma),"av."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.4)

} #fin de la boucle sur les actifs
