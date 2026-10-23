###############
# fct: Rdtcumul3D (pour des matrice Mat[,,])
###############
#fonction qui cumul les rendements annuel en dim 3
#Attention: on considère les rendements continus (sinon utiliser le param de la fct)
#
# crée le: 22/12/2017 par Sébastien Gallet
# modifiée le: 22/12/2017 par Sébastien Gallet
#
# Version : 1.0
#
# variables d entree#######################
# T maturité des projections
# NS nombre de simul
# Mat la matrice des rendemments à cumuler de la forme [N;T;Nombre d'actifs]
# Matcumul est la matrice "Mat" cumulée 
# gl : nombre d'années glissantes pour calcul rend
# si gl = 0 , alors toutes les années sont prise (par defaut gl=0)
# si gl = n , alors les n dernières années sont prises en comptes
# continu = Y si les taux sont continus, N s'ils sont annuels  (par defaut "Y")
###########################################

Rdtcumul3D<-function(Mat,gl=0,continu="Y",pas_t=1) {

NS<-dim(Mat[,,])[1]
Ts<-dim(Mat[,,])[2]
Nbactifs<-dim(Mat[,,])[3]
  
#initialisation
Matcumul<-array(0,c(NS,Ts,Nbactifs))
Matcumul[,1,]<-Mat[,1,]*pas_t
Matcumul[,2,]<-Mat[,2,]*pas_t

 if (continu=="Y")  {
   for(kw in 2:Ts){
    #si kw > gl alors on limite aux années glissantes gl
      if ((kw > gl+1) & (gl!=0)) { #+1 car decalage de la premiere colonne

      #calcul pour des taux continus
      Matcumul[,kw,]<-Matcumul[,kw-1,]+Mat[,kw,]*pas_t-Mat[,kw-gl,]*pas_t
      } else {
      #taux continus
      Matcumul[,kw,]<-Matcumul[,kw-1,]+Mat[,kw,]*pas_t
      }
   }
   #conversion du taux continu en taux annuel
   #Matcumul<-exp(Matcumul)-1
 } else {
   for(kw in 2:Ts){
      #si kw > gl alors on limite aux années glissantes gl
      if ((kw > gl+1) & (gl!=0)){
      #Ajout du taux nominal long
      #calcul pour des taux annuels
      Matcumul[,kw,]<-(1+Matcumul[,kw-1,])*(1+Mat[,kw,]*pas_t)/(1+Mat[,kw-gl,]*pas_t)-1 
      } else {
      #taux annuels
      Matcumul[,kw,]<-(1+Matcumul[,kw-1,])*(1+Mat[,kw,]*pas_t)-1
      }
    }
 }

rm(list=c('gl','kw','continu','NS','Ts'))
gc()

Matcumul

}