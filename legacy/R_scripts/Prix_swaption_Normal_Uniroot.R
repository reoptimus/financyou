###########################################
# fct: Prix_swaptions_normal (Bachelier)
###########################################
#fonction qui genere les prix des swaptions par formule de black dite normale
#utile pour retrouver les prix des swaptions à partir des données Bloomberg
#
# crée le: 05/09/2018 par Sébastien Gallet
# modifiée le:
#
# Version : 1
#
# variables d entree#######################
# Tdeb la maturité du swaption
# Tenor, Tenor
# S fin des flux et echange du nominal
# n temps en année entre deux échanges
# X strike
# sigma, Volatilité normale (données bloomberg)
# f0, forward instantanné issu de la courbe EIOPA
# r0 taux court à T=0 (ici Euribor 3m)
# P0t, prix des obligation observées sur la marché pour différentes maturité (années entières)
# reptravail, repertoire de travail
###########################################

Prix_swaption_Normal_Uniroot <- function(Ta,Tb,n,K,sigma,P0t,prixsw,pas_P0t)
{
    Ta<-Ta/pas_P0t+1 #passage en increments
    Tb<-Tb/pas_P0t+1 #passage en increments
    
    # calcul du taux swap forward entre Ta et Tb
    Sw_ab<-(P0t[Ta]-P0t[Tb])
    
    som<-0
    
      for (j in seq(Ta+n/pas_P0t,Tb,n/pas_P0t) ) {
        som<-n*P0t[j]+som
      }
    
    Sw_ab<-Sw_ab/som
  
    # calcul du prix de swaption par formul Normale
    d1<-(Sw_ab-K)/(sigma*(((Ta-1)*pas_P0t)^0.5))
    PS_Norm<-(sigma*(((Ta-1)*pas_P0t)^0.5))*(d1*pnorm(d1,0,1)+dnorm(d1,0,1))*som-prixsw
    return(PS_Norm)

  #libere la mémoire vive inutile
  rm(list=c('Ta','Tb','Sw_ab','som','d1','K','n','PS_Norm'))
  #rm(list=ls())
  gc()
  
} #fin fonction
  
