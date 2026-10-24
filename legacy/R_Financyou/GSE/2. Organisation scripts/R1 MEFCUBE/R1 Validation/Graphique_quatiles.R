
# visualisation ggplot des assets
setwd("E:/")
reptravail<-getwd()
reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")

#tracé pour la tranche deflateur en R
ListNomActifs<-c("DEFLATOR",paste("ZC_",seq(1:11)),"EQ_CAPITAL_CHANGE","EQ_DIVIDEND","PROP_CAPITAL_CHANGE","PROP_DIVIDEND","INFLATION","EQUITY_TOTAL_RETURN","PROP_TOTAL_RETURN")
nb_tr=1
ListNomActifs[nb_tr]
tr<-1/cube[,,nb_tr]

x<-1:length(cube[1,,nb_tr])
max<-apply(tr,MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(tr,MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(tr,MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(tr,MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(tr,MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(tr,MARGIN=2,FUN=quantile,probs=0.317)
#mean<-apply(tr,MARGIN=2,FUN=quantile,probs=0.5)
mean<-apply(tr,MARGIN=2,FUN=mean)



# tracé
plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(0,20),
     xlab="années",ylab="Taux ZC",main=paste("Quantiles des rdt prix ",ListNomActifs[nb_tr],sep=""))
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")
legend("topleft", inset=.01, title="Qantiles",
       c(expression(3*sigma),expression(2*sigma),expression(sigma),"moy."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)


# Tr n°
nb_tr=11+8
ListNomActifs[nb_tr]
tr<-cube[,,nb_tr]
# 
# x<-1:length(cube[1,,nb_tr])
# max<-apply(tr,MARGIN=2,FUN=quantile,probs=0.997)
# min<-apply(tr,MARGIN=2,FUN=quantile,probs=0.003)
# qet2max<-apply(tr,MARGIN=2,FUN=quantile,probs=0.954)
# qet2min<-apply(tr,MARGIN=2,FUN=quantile,probs=0.046)
# qetmax<-apply(tr,MARGIN=2,FUN=quantile,probs=0.683)
# qetmin<-apply(tr,MARGIN=2,FUN=quantile,probs=0.317)
# #mean<-apply(tr,MARGIN=2,FUN=quantile,probs=0.5)
# mean<-apply(tr,MARGIN=2,FUN=mean)
# 
# 
# # tracé
# plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(0,20),
#          xlab="années",ylab="Taux ZC",main=paste("Quantiles des ",ListNomActifs[nb_tr],sep=""))
# polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
# polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
# polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
# lines(x,mean,type="l",col="red")
# legend("topleft", inset=.01, title="Qantiles",
#        c(expression(3*sigma),expression(2*sigma),expression(sigma),"moy."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)


# Variables globales
N<-dim(cube[,,])[1]
T<-dim(cube[,,])[2]
NbAct<-dim(cube[,,])[3]

# Chargement des fonctions utilisées: cumul des rendements
source(paste(reptravail,"/R1 MEFCUBE/R1 Fonctions locale/F_Rdtcumul3D.R",sep=""))
source(paste(reptravail,"/R1 MEFCUBE/R1 Fonctions locale/F_Rdtcumul.R",sep=""))

#calcul des rendement des actifs cumulés
CumulESG<-array(0,c(N,T,NbAct))
CumulESG<-exp(Rdtcumul3D(cube))

#tracé pour la tranche n°
x<-1:length(CumulESG[1,,nb_tr])
max<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.317)
mean<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.5)

# tracé
plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(0,20),
     xlab="années",ylab="rendements cumulés",main=paste("Quantiles des prix rdt cumulés ",ListNomActifs[nb_tr],sep=""))
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")
legend("topleft", inset=.01, title="Qantiles",
       c(expression(3*sigma),expression(2*sigma),expression(sigma),"moy."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)


#calcul du cube cumule deflaté
CumulESGDefl<-CumulESG*array(rep(cube[,,1],dim(CumulESG)[3]),dim=dim(CumulESG))

#tracé pour la tranche n°
x<-1:length(CumulESGDefl[1,,nb_tr])
max<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.317)

# mean<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.5)
mean<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=mean)

# tracé
plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(-1,2),
     xlab="incr. temps",ylab="rendements cumulés defl.",main=paste("Rdt cumulés déflatés ",ListNomActifs[nb_tr],sep=""))
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")
legend("topleft", inset=.01, title="Qantiles",
       c(expression(3*sigma),expression(2*sigma),expression(sigma),"moy."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)


