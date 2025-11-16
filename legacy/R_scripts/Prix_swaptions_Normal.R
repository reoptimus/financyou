###########################################
# fct: Prix_swaptions_normal (Bachelier)
###########################################
#fonction qui genere les prix des swaptions par formule de black
#utile pour retrouver les prix des swaptions à partir des données Bloomberg
#
# crée le: 05/09/2018 par Sébastien Gallet
# modifiée le:
#
# Version : 1
#
# variables d entree#######################
# t la maturité du swaption
# Tdeb Tenor
# S fin des flux et echange du nominal
# n temps en année entre deux échanges
# X strike
# sigma, Volatilité normale (données bloomberg)
# f0, forward instantanné issu de la courbe EIOPA
# r0 taux court à T=0 (ici Euribor 3m)
# P0t, prix des obligation observées sur la marché pour différentes maturité (années entières)
# reptravail, repertoire de travail
###########################################

Prix_swaptions_normal <- function(fichier_swaptions,sortieRda,reptravail,pas_P0t)
{
  
  #Paramètres figés pour démonstration à effacer
  # fichier_swaptions<-"Swaptions_V2.csv"
  # sortieRda<-"Prix_swaptions_bloomberg"
  # reptravail<-'\\\\intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG_V2/2. Organisation scripts/'
  # ##############################################
  sw_prix<-read.csv( file= paste(reptravail,"R4 CALIBRAGE/R4 IN/",fichier_swaptions, sep="") , header=TRUE , sep=";")
  
  # Chargement des prix des ZC########
  load(paste(reptravail,"R2 CUBE/R2 IN/","Prix_P0t_interp.Rda", sep=""))
  
  #initialisation
  nb_sw<-length(sw_prix[1,])-1
  PS_Norm<-array(0,dim=c(1,(nb_sw+1)))
  PS_Norm_mat<-array(0,dim=c(6,(nb_sw+1)))
  #boucle sur les differents swaptions présent dans le fichier d'import
  for (nb in 1:nb_sw){
  
    n<-sw_prix[3,nb] # swaps jambes de n ans
    t<-sw_prix[1,nb]/pas_P0t+1 #maturité en année remis en pas-increment qui part de 0
    Tdeb<-sw_prix[2,nb]/pas_P0t+1 #Tenor en année remis en pas-increment
  
    K<-sw_prix[4,nb]
    sigma <- sw_prix[5,nb]/10000 #attention unité, en bps dans le fichier XL
    
    Ta<-t #en increments
    Tb<-(t+Tdeb)-1 #en increments
    
    # calcul du taux swap forward entre Ta et Tb
    Sw_ab<-(P0t_interp[Ta]-P0t_interp[Tb])
    
    som<-0
    
      for (j in seq(Ta+n/pas_P0t,Tb,n/pas_P0t)) {
        som<-n*P0t_interp[j]+som
      }
    
    Sw_ab<-Sw_ab/som
  
    # calcul du prix de swaption par formul Normale
    d1<-(Sw_ab-K)/(sigma*(((Ta-1)*n)^0.5))
    PS_Norm[nb+1]<-(sigma*(((Ta-1)*n)^0.5))*(d1*pnorm(d1,0,1)+dnorm(d1,0,1))*som
    
  } #fin boucle nb swaptions
  
  PS_Norm<-as.data.frame(PS_Norm)
  names(PS_Norm)<-names(sw_prix)
  PS_Norm[1,1]<-"Prix calculé"
  PS_Norm_mat<-rbind(sw_prix,PS_Norm)

  save(PS_Norm_mat,file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/",sortieRda,".Rda", sep=""))
  
  #libere la mémoire vive inutile
  rm(list=c('Ta','Tb','Sw_ab','som','d1','sigma','Tdeb','t','nb','j','K','n','PS_Norm','nb_sw'))
  #rm(list=ls())
  gc()
  
} #fin fonction
  
