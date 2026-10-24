#################################################
# script pour la visualisation des sorties GSE
# fait le 21/12/2019
#################################################

Visu_quant<- function (reptravail,tranche,noms_list,sum_cuml) {
# setwd("E:/")
# reptravail<-getwd()
# reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")
# 
# # matrice (N,Tp)
# tranche<-Rt

# params
N<-dim(tranche[,])[1]
Tmp<-dim(tranche[,])[2]
top<-max(sum_cuml)*4
ceil<-0

x<-1:Tmp
max<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.317)
#mean<-apply(cube[,,nb_tr],MARGIN=2,FUN=quantile,probs=0.5)
#mean<-apply(tranche,MARGIN=2,FUN=mean)

# trac? non-cumul?
plot(NULL,NULL,xlim=c(min(x),max(x)), ylim=c(ceil,top), #c(0,10),
     xlab="time",ylab="Rate")
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
#lines(x,mean,type="l",col="red")

} #fin de la fonction
