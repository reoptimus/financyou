######################
#
# Stripping : fonction de strip du profil financier utilisateur
# Version Shinyapps (chemin different)
#
# modiifie le 06/02/2020
# par Sebastien Gallet

stripping<-function (pas_E,a) {

#Valeurs initiales: 
  # reptravail<-"E:/R_Financyou/MOCA"
  # pas_E<-5000 #pas de 3 eur
  # a<--sum_cuml

date<-1:length(a)
# plot(date,a,type="l")

#Construction de la base initiale
baseInitiale <- data.frame(date,t(a))
pas_t<-ceiling(max(a[2:length(baseInitiale[,1])]-a[1:(length(baseInitiale[,1])-1)])/(pas_E))
#on en deduit le pas de temps necessaire pour paver l'espace des montants à minima
pas_t<-1/pas_t

#Date souhaitée, ici toutes les années de 1970 à 2014
date2<-seq(1,length(date),pas_t)

#Calcul par interpolation
resultat<-approx(date, a, xout = date2, method="linear", ties="ordered")$y
baseFinale=data.frame(date2,resultat)

# plot(baseFinale)

#algo recalibrage sur les tranches en Euros
if(baseFinale[1,2]>baseFinale[2,2]){
  tr_ref<-ceiling(baseFinale[1,2]/pas_E)-1
} else {
  tr_ref<-floor(baseFinale[1,2]/pas_E)
}

indice<-1
baseFinale2<-array(0,dim=c(1000,3)) #colonne: M,T,nb de points

baseFinale2[1,1]<-tr_ref
  baseFinale2[1,2]<-baseFinale[1,1]
  baseFinale2[1,3]<-1
 
  for (i in 2:length(baseFinale[,2])) {
    if (baseFinale[i,2]>=(tr_ref*pas_E) & baseFinale[i,2]<=((tr_ref+1)*pas_E)) { #si le montant dans la tranche ref
      baseFinale2[indice,1]<-tr_ref
      baseFinale2[indice,2]<-baseFinale2[indice,2]+baseFinale[i,1]
      baseFinale2[indice,3]<- baseFinale2[indice,3]+1
    } else {
      indice<-indice+1
      if (baseFinale[i,2]<(tr_ref*pas_E)) { #on sort de la tranche par le bas
        tr_ref<-tr_ref-1
      }else { #on sort de la tranche par le haut
        tr_ref<-tr_ref+1
      }
      baseFinale2[indice,1]<-tr_ref
      baseFinale2[indice,2]<-baseFinale2[indice,2]+baseFinale[i,1]
      baseFinale2[indice,3]<- baseFinale2[indice,3]+1
    }
}
baseFinale2[,2]<-baseFinale2[,2]/baseFinale2[,3]

 #nettoyage
baseFinale2[is.na(baseFinale2)]<-0
baseFinale2 <- subset(baseFinale2, baseFinale2[,1] != 0)
baseFinale2[1,2]<-1 # on  remet le premier point au temp 1
# plot(baseFinale2[,2],baseFinale2[,1])

# ajout de point fictif pour retomber a zero
baseFinal3<-array(0,dim=c(1000,2)) #colonne: M,T,nb de points
#ajout des points montants chusqu au demarrage de baseFinale2
for (i in 1:baseFinale2[1,1]) {
  baseFinal3[i,1]<-i
  baseFinal3[i,2]<-i*1/baseFinale2[1,1]
}
#ajout de la courbe baseFinale2
baseFinal3[baseFinale2[1,1]:(length(baseFinale2[,1])+baseFinale2[1,1]-1),1:2]<-baseFinale2[,1:2]
#ajout des points descendant jusqu'a zero
#point de reprise du remplissage
j<-baseFinale2[1,1]+length(baseFinale2[,1])-1
for (i in 1:(baseFinale2[length(baseFinale2[,1]),1]-1)) {
  baseFinal3[j+i,1]<-baseFinale2[length(baseFinale2[,1]),1]-i
  baseFinal3[j+i,2]<-baseFinale2[length(baseFinale2[,1]),2]+i*1/baseFinale2[length(baseFinale2[,1]),1]
}
#nettoyage
baseFinal3[is.na(baseFinal3)]<-0
baseFinal3 <- subset(baseFinal3, baseFinal3[,1] != 0)

# plot(baseFinal3[,2],baseFinal3[,1])

#algo de striping
min_t<-baseFinale2[1,1] #periode min du stripping
max_t<-length(baseFinale2[,1])+min_t+1 #periode max du stripping
point_max<-0 #compte l'atteinte de point max
point_min<-0
k<-0 #compatage des segments horizontaux
Tr<-array(0,dim=c(1000,3)) #t_debut,t_fin,Montant de la tranche

i=2
for (i in 2:(length(baseFinal3[,2])-1) ) {

  if (baseFinal3[i,1]>baseFinal3[i+1,1] & baseFinal3[i-1,1]<baseFinal3[i,1] ) {
   #atteinte d'un point haut
    Tr_max<-baseFinal3[i,1]
    point_max<-point_max+1
  }
  if (baseFinal3[i,1]<baseFinal3[i+1,1] & baseFinal3[i-1,1]>baseFinal3[i,1] ) {
    #atteinte d'un point bas
    #Tr_min<-baseFinal3[i,1]
    t_max<-i #periode du min et donc temps max du decoupage
    point_min<-point_min+1
  }
  
  if (point_max==1 & point_min==1) {
    point_max<-0
    point_min<-0
    #couple min et max->decoupage en strip
    for (j in 1:(Tr_max-1)){ #on ne fait pas le point final haut
      k<-k+1
      if (length(which(baseFinal3[min_t:t_max,1]==j))==0) {
        Tr[k,1]<-baseFinal3[min_t,2]
        Tr[k,2]<-baseFinal3[t_max,2]
        Tr[k,3]<-j
      } else {
        if (length(which(baseFinal3[min_t:t_max,1]==j))==1) {
          if (baseFinal3[min_t,1]>baseFinal3[t_max,1]){
            Tr[k,1]<-baseFinal3[min_t,2]
            Tr[k,2]<-baseFinal3[(which(baseFinal3[min_t:t_max,1]==j)[1]+min_t-1),2]
            Tr[k,3]<-j
          } else {
            #si Tr min < Tr max
            Tr[k,1]<-baseFinal3[(which(baseFinal3[min_t:t_max,1]==j)[1]+min_t-1),2]
            Tr[k,2]<-baseFinal3[t_max,2]
            Tr[k,3]<-j
          }      
        } else { #s'il y a deux point dans la tranche 
          
          Tr[k,1]<-baseFinal3[(which(baseFinal3[min_t:t_max,1]==j)[1]+min_t-1),2]
          Tr[k,2]<-baseFinal3[(which(baseFinal3[min_t:t_max,1]==j)[2]+min_t-1),2]
          Tr[k,3]<-j
          
        }
      }
      
    }
    min_t<-t_max
  }
}#fin boucle for

#manque la derniere redescente entre min_t et max_t
for (j in 1:(Tr_max-1)){
  k<-k+1
  if (length(which(baseFinal3[min_t:max_t,1]==j))==0) {
    Tr[k,1]<-baseFinal3[min_t,2]
    Tr[k,2]<-baseFinal3[max_t,2]
    Tr[k,3]<-j
  } else {
    if (length(which(baseFinal3[min_t:max_t,1]==j))==1) {
      if (baseFinal3[min_t,1]>baseFinal3[max_t,1]){
        Tr[k,1]<-baseFinal3[min_t,2]
        Tr[k,2]<-baseFinal3[(which(baseFinal3[min_t:max_t,1]==j)[1]+min_t-1),2]
        Tr[k,3]<-j
      } else {
        #si Tr min < Tr max
        Tr[k,1]<-baseFinal3[(which(baseFinal3[min_t:max_t,1]==j)[1]+min_t-1),2]
        Tr[k,2]<-baseFinal3[max_t,2]
        Tr[k,3]<-j
      }      
    } else { #s'il y a deux point dans la tranche 
        
        Tr[k,1]<-baseFinal3[(which(baseFinal3[min_t:max_t,1]==j)[1]+min_t-1),2]
        Tr[k,2]<-baseFinal3[(which(baseFinal3[min_t:max_t,1]==j)[2]+min_t-1),2]
        Tr[k,3]<-j

    }
  }
  
}

#nettoyage
Tr[is.na(baseFinal3)]<-0
Tr <- subset(Tr, Tr[,1] != 0)

Tr1<-Tr
#reassemblage des lignes
nbligne<-length(Tr1[,1])

for (j in 1:nbligne) {
  for (i in 2:nbligne){
    if (Tr1[j,2]==Tr1[i,1] & Tr1[j,3]==Tr1[i,3] & (Tr1[j,1]!=0)) {
      Tr1[j,2]<-Tr1[i,2]
      #on efface le segment i
      Tr1[i,1:3]<-c(0,0,0)
    } # if
  } #boucle i
} #boucle j
#nettoyage
Tr1 <- subset(Tr1, Tr1[,1] != 0)
Tr1 <- subset(Tr1, Tr1[,2] != 0)

return(Tr1)

#plot
# plot(0,0,xlim=c(1,max(Tr1[,2])),ylim=c(0,max(Tr1[,3])))
# for (i in 1:length(Tr1[,1])) {
#   lines(c(Tr1[i,1],Tr1[i,2]),c(Tr1[i,3],Tr1[i,3]))}


} # fin de la fonction

