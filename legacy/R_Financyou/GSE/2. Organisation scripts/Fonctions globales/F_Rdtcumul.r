###############
# fct: Rdtcumul
###############
#fonction qui cumul les rendements annuel
#Attention: on considère les rendements continus
#
# crée le: 26/10/2017 par Sébastien Gallet
# modifiée le: 26/10/2017 par Sébastien Gallet
#
# Version : 1.0
#
# variables d entree#######################
# T maturité des projections
# NS nombre de simul
# Mat la matrice des rendemments à cumuler de la forme [N;T]
# Matcumul est la matrice "Mat" cumulée 
# gl : nombre d'années glissantes pour calcul rend
# si gl = 0 , alors toutes les années sont prise (par defaut gl=0)
# si gl = n , alors les n dernières années sont prises en comptes
# continu = Y si les taux sont continu, N s'ils sont annuels  (par defaut "Y")
###########################################

Rdtcumul<-function(Mat,gl=0,continu="Y") {

NS<-nrow(Mat)
Ts<-ncol(Mat)
  
#initialisation
Matcumul<-matrix(0,nrow=NS,ncol=Ts)
Matcumul[,1]<-Mat[,1]
Matcumul[,2]<-Mat[,2]

 if (continu=="Y")  {
   for(kw in 3:Ts){
    #si kw > gl alors on limite aux années glissantes gl
      if ((kw > gl+1) & (gl!=0)) { #+1 car decalage de la premiere colonne

      #calcul pour des taux continus
      Matcumul[,kw]<-Matcumul[,kw-1]+Mat[,kw]-Mat[,kw-gl]
      } else {
      #taux continus
      Matcumul[,kw]<-Matcumul[,kw-1]+Mat[,kw]
      }
   }
   #conversion du taux continu en taux annuel
   #Matcumul<-exp(Matcumul)-1
 } else {
   for(kw in 3:Ts){
      #si kw > gl alors on limite aux années glissantes gl
      if ((kw > gl+1) & (gl!=0)){
      #Ajout du taux nominal long
      #calcul pour des taux annuels
      Matcumul[,kw]<-(1+Matcumul[,kw-1])*(1+Mat[,kw])/(1+Mat[,kw-gl])-1 
      } else {
      #taux annuels
      Matcumul[,kw]<-(1+Matcumul[,kw-1])*(1+Mat[,kw])-1
      }
    }
 }

rm(list=c('gl','kw','continu','NS','Ts'))
gc()

Matcumul

}