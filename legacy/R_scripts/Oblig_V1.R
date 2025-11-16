###############
# fct: Obligation: calcul de l'?volution des prix d'obligation et tomb?s de coupons
###############
#fonction qui genere les obligations a partir des ZC
#
# modifi?e le: 04/08/2019 par Sebastien Gallet
#
# Version : 1
#
# variables d entree#######################
# nom_ZC = nom fichier Rdata contenant les ZC
# pas = pas de calcul en ann?es des ZC
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
###########################################

Oblig <- function(matu,nom_sortie_OAT,pas,reptravail,limit_default,ab_default,cube)
{
    #################################### A effacer
  #Param?tres fig?s pour d?monstration
  # nom_sortie_OAT<-"Tr-OAT"
  # pas<-0.5
  # limit_default<-log(1+0.2) #limite de rendement sur l'annee avant defaut
  # ab_default<-log(1-0.3) #perte en % du prix sur le rendement annuel
  # matu<-10 # maturite de l oblig en increment
  # setwd("E:/")
  # reptravail<-getwd()
  # reptravail<-paste0(reptravail,"R_Financyou/GSE+")

  source(file=paste0(reptravail,"/R2 CUBE+/R2 Fonctions locale/F_Rdtcumul.R"))
  
  #load des ZC
  # load(file=paste(reptravail,nom_cub_plac,sep=""))
  nb_ZC<-dim(cube)[3]-8
  ZC<-cube[,,2:(nb_ZC+1)]
  #plot(apply(ZC[,1:120,10],2,mean))
  Defl<-cube[,,1] #deflator
  
  N<-dim(ZC)[1]
  proj<-dim(ZC)[2] #nb de pas projete
  d<-dim(ZC)[3] # 40 durations calcul?e
 
  
  print(paste0("d?but du calcul des obligations OAT ",matu," ans"))
  flush.console()

  #on considere l'ann?e pr?c?dente au pair soit Oblig=1, on calcul le coupon, puis on calcul le prix de l'obligation de lannee +1
  coupon_0<-(1-ZC[,1:(proj-1),matu])/apply(ZC[,1:(proj-1),1:matu],c(1,2),sum)
  coupon_1<-(1-ZC[,2:proj,matu])/apply(ZC[,2:proj,1:matu],c(1,2),sum)
    #coupon_0<-ifelse(coupon_0<0,0,coupon_0)
    #coupon_1<-ifelse(coupon_1<0,0,coupon_1)
  # plot(apply(coupon_0[,],2,mean))
  
  P_OAT_0<-1 #emission au pair
  P_OAT_1<-array(0,dim=dim(cube[,1:(dim(cube[,,2:(nb_ZC+1)])[2]-1),2:(nb_ZC+1)]))
  Rdt_OAT<-array(0,dim=dim(cube[,1:(dim(cube[,,2:(nb_ZC+1)])[2]-1),2:(nb_ZC+1)]))
  
  P_OAT_1<-(1+coupon_1)^pas*(apply(ZC[,2:proj,1:(matu)],c(1,2),sum)*coupon_0+ZC[,2:proj,(matu)])
  P_OAT_1<-array(mapply(max,P_OAT_1,0.0001),dim=dim(P_OAT_1)) # on corrige les prix trop pret de 0 ou n?gatifs
  #plot(apply(P_OAT_1,2,mean))
  
  Rdt_OAT<-log(P_OAT_1/P_OAT_0)
  #plot(apply(Rdt_OAT,2,mean))
  
  Rdt_OAT<-cbind(Rdt_OAT,Rdt_OAT[,length(Rdt_OAT[1,])]) # doublement de la derni?re colonne
  
  # plot(apply(P_OAT_1,2,mean),type="l",col="red")#*Defl[,2:proj]/Defl[,1:(proj-1)]
  # lines(rep(1,(proj-1)))
  # plot(apply(exp(Rdtcumul(Rdt_OAT))*Defl[,],2,mean),type="l",col="red")  #*Defl[,]
  # lines(rep(1,proj))
  
  # default quand le rendement annuel<limit_default . Perte de ab_default sur le pas_t consid?r? (defaut partiel)
  Rdt_OAT[which( Rdt_OAT>limit_default,arr.ind=1)[,]]<-ab_default

  #affichage graphique des quantiles
  # x<-1:length(Rdt_OAT[1,])
  # max<-apply(Rdt_OAT[,],MARGIN=2,FUN=quantile,probs=0.997)
  # min<-apply(Rdt_OAT[,],MARGIN=2,FUN=quantile,probs=0.003)
  # qet2max<-apply(Rdt_OAT[,],MARGIN=2,FUN=quantile,probs=0.954)
  # qet2min<-apply(Rdt_OAT[,],MARGIN=2,FUN=quantile,probs=0.046)
  # qetmax<-apply(Rdt_OAT[,],MARGIN=2,FUN=quantile,probs=0.683)
  # qetmin<-apply(Rdt_OAT[,],MARGIN=2,FUN=quantile,probs=0.317)
  # #mean<-apply(Rdt_OAT[,],MARGIN=2,FUN=quantile,probs=0.5)
  # mean<-apply(Rdt_OAT[,],MARGIN=2,FUN=mean)
  # 
  # plot(NULL,NULL,xlim=c(min(x),40),ylim=c(-0.5,0.3),
  #      xlab="time",ylab="Rate",main=paste("Quantiles of ","Assurance Vie",sep=""))
  # polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
  # polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
  # polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
  # lines(x,mean,type="l",col="red")
  #legend("topleft", inset=.01, title="Qantiles",
   #      c(expression(3*sigma),expression(2*sigma),expression(sigma),"av."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)
  
  
  print(paste("fin de calcul des Rdt des OAT",matu,sep=""))
  flush.console()
  
  #savegarde au format Rdata de la mat des ZC
  save(Rdt_OAT, file=paste0(reptravail,"/R2 CUBE+/R2 OUT/",nom_sortie_OAT,matu,".Rda"))
 
  #libere la m?moire vive inutile
  rm(list=c())
  #rm(list=ls())
  gc()
  
} #fin fonction

