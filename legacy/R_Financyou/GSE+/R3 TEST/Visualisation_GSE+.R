#################################################
# script pour la visualisation des sorties GSE+
# fait le 17/12/2019
#################################################
library(ggplot2)

setwd("D:/")
reptravail<-getwd()
reptravail<-paste0(reptravail,"R_Financyou/GSE+")
ad_GSE<-"/R2 CUBE+/R2 OUT/"
GSE<-"GSE+.Rda"#Test_ReO.V1.Rda"
pas_t<-0.5 # pas du GSE
load(paste(reptravail,ad_GSE,GSE,sep=""))

list_actifs<-c("Monetaire",
               "Prix Actions",
               "div actions",
               "Prix + div actions",
               "Prix Immobilier",
               "Loyers immo",
               "Prix + Loyers immo",
               "obligations souveraines AA",
               "obligations souveraines A",
               "obligations souveraines BBB",
               "obligations corpo AA",
               "obligations corpo A",
               "obligations corpos BBB",
               "assurance vie EUR",
               "assurance vie EUR_V2",
               "assurance vie UC")

# params
N<-dim(cube_placement[,,])[1]
Tmp<-dim(cube_placement[,,])[2]
NbAct<-dim(cube_placement[,,])[3]

#calcul du cube_placement cumule
CumulESG<-array(0,dim=c(N,Tmp,(NbAct)))
CumulESG<-cube_placement[,,]

#enregistrement de (E,V) au temps d'arret tarr
tarr<-c(5,10,20)
mat_EV<-array(0,dim=c(NbAct,3,length(tarr)))

#######################################
# Visualisation
for (i in 1:length(list_actifs)) {
nb_tr=i #deflator nb
mat_EV[i,1,]<-list_actifs[nb_tr]


x<-1:length(CumulESG[1,,nb_tr])
max<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.317)
mean<-apply(CumulESG[,,nb_tr],MARGIN=2,FUN=mean)

mat_EV[i,2,]<-apply(CumulESG[,tarr/pas_t,nb_tr],2,mean)
mat_EV[i,3,]<-apply(CumulESG[,tarr/pas_t,nb_tr],2,sd)

plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(0,10),
     xlab="time",ylab="Rate",main=list_actifs[nb_tr])
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")

# legend("topleft", inset=.01, title="Qantiles",
#        c(expression(3*sigma),expression(2*sigma),expression(sigma),"av."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)
} # fin de la boucle sur les tranches

# ggplot(mat_EV, aes(x = mat_EV[,3], y = mat_EV[,2])) +
#   geom_point()
tarr<-3
plot(mat_EV[,3,tarr],mat_EV[,2,tarr],type="p",col="red",main="Hist,0.5,1000,0.1,-0.1") #,xlim=c(0,1.5),ylim=c(0.8,4)
# points(mat_EV[,3,1],mat_EV[,2,1],col="blue")
# points(mat_EV[,3,2],mat_EV[,2,2],col="green")
points(0,0,pch=19,col="black")
list<-seq(0,1,0.1)
lines(list,rep(0,length(list)))
text(mat_EV[,3:2,tarr], as.character(1:length(list_actifs)), cex=0.5, pos=3,col="red")

#####################################
# Marting
#########
# for (i in 1:length(list_actifs)) {
#   nb_tr=i #deflator nb
#   list_actifs[nb_tr]
#   
# x<-1:length(CumulESGDefl[1,,nb_tr])
# max<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.997)
# min<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.003)
# qet2max<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.954)
# qet2min<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.046)
# qetmax<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.683)
# qetmin<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.317)
# 
# # mean<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.5)
# mean<-apply(CumulESGDefl[,,nb_tr],MARGIN=2,FUN=mean)
# 
# # trac
# plot(NULL,NULL,xlim=c(min(x),max(x)),ylim=c(0,2),
#      xlab="time",ylab="rates",main=paste("deflated agg returns ",list_actifs[nb_tr],sep=""),cex.main=0.8)
# polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
# polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
# polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
# lines(x,mean,type="l",col="red")
# legend("topleft", inset=.01, title="Qantiles",
#        c(expression(3*sigma),expression(2*sigma),expression(sigma),"av."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.4)

#} #fin de la boucle sur les actifs
