###############
# fct: Calib_Taux F0
###############
# Calcul P0 et f0 qui fit la courbe EOIPA interpolées au pas_t
#
# crée le: 02/12/2018 par Sébastien Gallet
# modifiée le: 19/04/2019
#
# Version : 2.2
# modification de la lecture excel package "xlsx" -> "readxl"
#
# variables d entree#######################
# Param_EOIPA = fichier Excel avec les données de la courbes EOIPA
# nom_sortie = nom donne a la variable de sortie
# pas_t = le pas de temps en année utilisé (ex:1/12 pour mensuel)
# sc = pays considéré ds les données EIOPA (colonne)
#################


Calib_Tauxf0 <- function(Param_EIOPA,reptravail,pas_t,sc=2)
{ #debut fonction
  
  ################
  #Paramètres internes
  ################  
  #install.packages('xlsx', repo='http://nbcgib.uesc.br/mirrors/cran/')
  # pas_t<-0.005
  # sc=2
  # Param_EIOPA<-"EIOPA_avril_2018_FRANCE.xlsx"
  # reptravail<-'E:/R_Financyou/GSE/2. Organisation scripts'

  nom_sortie_P0t<-paste("Prix_P0t_interp_",sc,sep="")
  nom_sortie_f0t<-paste("f0t_liss_",sc,sep="")
  
  ############################
  #chargement des données EIOPA
  # Basi RFR spot no VA: feuille 3
  # Data :ligne 11-160
  # EURO: col 3 , France: col 13sheetIndex = 
  Mat_EIOPA<-read.xlsx(paste0(reptravail,"/R4 CALIBRAGE/R4 IN/",Param_EIOPA),sheetIndex = 1)
  Mat_EIOPA<-as.data.frame(Mat_EIOPA)
  plot(1:length(Mat_EIOPA[,sc]),Mat_EIOPA[,sc], main="Taux EIOPA")

  ############################
  # calcul des P0t à partir des f0t
  P0t<-1/(1+Mat_EIOPA[,sc])^(1:length(Mat_EIOPA[,sc]))
  P0t<-c(1,P0t)
  
  #verification par le prix par maturité
  ###########################
  plot(P0t,main="Prix ZC issus de EIOPA",type="o",cex=0.5)
  
  #interpolation sur le pas de temps du GSE: pas_t
  P0t_interp<-array(1,dim=c(1,length(Mat_EIOPA[,sc])*(1/pas_t)+1))
  
  # type d'interpolation : linéaire ou spline3
  #P0t_interp<-approx(1:length(P0t),P0t,xout=seq(1,length(P0t_interp)*pas_t,pas_t),method="linear", ties="ordered")$y
  P0t_interp<-spline(1:length(P0t),P0t,n=length(P0t)/pas_t-1,method="natural",xmin=1,xmax= length(P0t))$y
  # plot(P0t_interp,main="Prix ZC interpolés de EIOPA",type="o",cex=0.5)
  
  #calcul de f0t
  f0t_interp<-log(P0t_interp)
  df0t_interp_1<--(f0t_interp[2:length(f0t_interp)]- f0t_interp[1:(length(f0t_interp)-1)])/pas_t #dT de la courbe EIOPA = 1 an
  df0t_interp_2<--(f0t_interp[3:length(f0t_interp)]- f0t_interp[1:(length(f0t_interp)-2)])/(2*pas_t)
  
  f0t_interp[2:(length(df0t_interp_2)+1)]<-df0t_interp_2
  f0t_interp[1]<-df0t_interp_1[1]
  f0t_interp[length(f0t_interp)]<-df0t_interp_1[length(df0t_interp_1)]
  f0t_interp<-c(0,f0t_interp)
  
  #plot( f0t_interp[1:(150/pas_t)],type='l', main="f0 interpolée issu de EIOPA")
  
  #Lissage de f0t pour an> 50 ans
  f0t_liss<-f0t_interp
  gl<-20 #nb années glissantes pour le lissage
  deb_liss<-60 #debut du lissage en annnées

  for (i in 1:(gl/pas_t)) { #calcul moyenne glissante
  f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]<-f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]+f0t_interp[(deb_liss/pas_t+i):(length(f0t_interp)-gl/pas_t+i)]
  }

  f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]<- f0t_liss[(deb_liss/pas_t):(length(f0t_interp)-gl/pas_t)]/(gl/pas_t+1)
  f0t_liss[(length(f0t_interp)-gl/pas_t+1):length(f0t_interp)]<-f0t_liss[length(f0t_interp)-gl/pas_t] #prolongation de la dernière moyenne sur les gl dernières années
  
  plot(1:length(f0t_liss),f0t_liss,type='l',main="f0 lissée")
  
  #f0t_liss<-as.double(smooth.spline(f0t_liss,spar=-log10(pas_t)/1.5, all.knots = TRUE)$y)
  #lines(1:length(f0t_liss),f0t_liss,type="l",col="red")
  
  #enregistrement des prix ZC P0t dans le repertoire "in"
  save(P0t_interp,file = paste(reptravail,"/R4 CALIBRAGE/R4 OUT/",nom_sortie_P0t,".Rda", sep=""))
  #enregistrement des prix f0t dans le repertoire "in"
  save(f0t_liss, file=paste(reptravail,"/R4 CALIBRAGE/R4 OUT/",nom_sortie_f0t,".Rda", sep=""))
  
  rm(list=c("df0t_interp_1","df0t_interp_2","f0t_interp","P0t"))

} #fin fonction
