###############
# fct: Calib_Taux F0
###############
#fonction f0 qui fit la courbe EOIPA
#
# crée le: 11/06/2018 par Sébastien Gallet
# modifiée le: 
#
# Version : 1
#
# variables d entree#######################
# Param_EOIPA = fichier Excel avec les données de la courbes EOIPA
# nom_sortie = nom donne a la variable de sortie
# pas_t = le pas de temps en année utilisé (ex:1/12 pour mensuel)
#################

Calib_Tauxf0 <- function(curve_EIOPA,reptravail,pas_t)
{ #debut fonction
  
  ################
  #Paramètres internes
  ################  #install.packages("xlsx")
  library("xlsx")
 
  nom_sortie_P0t<-"Prix_P0t_interp"
  nom_sortie_f0t<-"f0t_liss"
  ################

  P0t<-1/(1+curve_EIOPA)^(1:length(curve_EIOPA))
  P0t<-c(1,P0t)
  #########################
  # plot(P0t,main="Prix ZC issus de EIOPA",type="l")
  
  #interpolation sur le pas de temps du GSE: pas_t
  P0t_interp<-array(1,dim=c(1,length(curve_EIOPA)*(1/pas_t)+1))
  
  # type d'interpolation : linéaire ou spline3
  #P0t_interp<-approx(1:length(P0t),P0t,xout=seq(1,length(P0t_interp)*pas_t,pas_t),method="linear", ties="ordered")$y
  P0t_interp<-spline(1:length(P0t),P0t,n=length(P0t)/pas_t-1,method="natural",xmin=1,xmax= length(P0t))$y

  #calcul de f0t
  f0t_interp<-log(P0t_interp)
  f0t_interp<--(f0t_interp[2:length( f0t_interp)]- f0t_interp[1:(length( f0t_interp)-1)])/pas_t #dT de la courbe EIOPA = 1 an
  # plot( f0t_interp[1:(150/pas_t)],type='l', main="f0 interpolée issu de EIOPA")
  
  #Lissage de f0t pour an> 50 ans
  f0t_liss<-f0t_interp
  gl<-20 #nb années glissantes pour le lissage
  deb_liss<-60 #debut du lissage en annnées
  
  for (i in 1:(gl/pas_t)) { #calcul moyenne glissante
  f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]<-f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]+f0t_interp[(deb_liss/pas_t+i):(length(f0t_interp)-gl/pas_t+i)]
  }
  
  f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]<- f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]/(gl/pas_t+1)
  f0t_liss[(length(f0t_interp)-gl/pas_t+1):length(f0t_interp)]<-f0t_liss[length(f0t_interp)-gl/pas_t] #prolongation de la dernière moyenne sur les gl dernières années
  plot(f0t_liss,type='l',main="f0 lissée")
  
  #enregistrement des prix ZC P0t dans le repertoire "OUT"
  save(P0t_interp,file = paste(reptravail,"R4 CALIBRAGE/R4 OUT/",nom_sortie_P0t,".Rda", sep=""))
  #enregistrement des prix f0t dans le repertoire "in"
  save(f0t_liss, file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/",nom_sortie_f0t,".Rda", sep=""))
  
  #efface les variables utilisées pour les calculs
  rm(list=ls())
  gc()
  
} #fin fonction
