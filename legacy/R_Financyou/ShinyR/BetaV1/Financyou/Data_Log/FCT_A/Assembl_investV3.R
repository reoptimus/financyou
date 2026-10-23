#########################
#
# Assemblage invest
#
# assemblage des investissements
# utilise d'un cote la liste de strip et de l'autre les resultats des placements optimum par Horizon
#
# Version 2 : integration de la partie contrainte (emprunt ? soltot)
# modifiee le 26/05/2020 (chemin shinyapps)
# par S?bastien Gallet
#
########################

Assembl_invest<-function(soltoti,Tr1,GSEpp,sum_cuml){
  
  # seuil_filtre<-0.02 # seuil filtre pour la visualisation des poches de placements
  # list_placements<-list_placements_compl
  # sum_cuml<--sum_cuml
  # GSEpp<-GSEpp_cuml  # dim(GSEpp)
  # Tr1<-mat_strip
  # soltoti<-soltot

  # definition des variables internes
Nb_plac<-dim(soltoti)[1]
Horizon_max<-dim(soltoti)[2] # en pas_t
Ns<-dim(GSEpp)[1] # Nb de scenario

Mat_result<-array(0,dim=c(Nb_plac,Horizon_max))
# dim(Mat_result)
Rdt_terme<-array(0,dim=c(Ns,Nb_plac,Horizon_max))
Rdt_liquide<-array(0,dim=c(Ns,Nb_plac,Horizon_max))
Mat_strip<- cbind(floor(Tr1[,1]),ceiling(Tr1[,2])+1 )
Mat_strip[,2]<-(Mat_strip[,2]-Mat_strip[,1]) 
Mat_strip <- subset(Mat_strip, Mat_strip[,1] != 0)
Mat_strip <- subset(Mat_strip, Mat_strip[,2] != 0)
Nb_strip<-dim(Mat_strip)[1] # les donn?es sont 1:debut, 2:fin, 3: le capital au moment de l'invest

i=1
for (i in 1:Nb_strip) { # boucle sur les strip
  Tp_deb<-Mat_strip[i,1] # debut de l'investissement
  D<-Mat_strip[i,2]
  Tp_deb<-min(Tp_deb,horiz-1)
  D<-min(D,horiz)
  fin<-min((Tp_deb+D-1),horiz)
  
  if (D!=0) {
    
    # tranche de placement en pourcent: debut: Tp_debut , fin: Tp_debut+D-1 , pour tabl_pourc_cont0 avec renormalisation
    ajout<-soltoti[,D,Tp_deb:fin]
    # apply(ajout,2,sum)
    # dim(soltoti)
    
    Mat_result[,Tp_deb:fin]<-ajout+Mat_result[,Tp_deb:fin]
    # dim(ajout) == dim(Mat_result[,(Tp_deb):fin])  # dim(Mat_result)
    # apply(Mat_result,2,sum)
    # calcul pour les Ns trajectoire ds rendements ponderes pour un investissement a terme
    if (length(dim(GSEpp[,(Tp_deb):fin,D,]))!=3) { # cas D=1, la dim change
      ajout_Rdt_terme<-GSEpp[,Tp_deb:fin,D,] * aperm( array(rep(as.matrix(ajout),Ns),dim=c(length(ajout[,1]),length(ajout[1,]),Ns)) ,c(3,1,2))[,,1]
    } else {
      ajout_Rdt_terme<-aperm(GSEpp[,Tp_deb:fin,D,],c(1,3,2)) * aperm( array(rep(ajout,Ns),dim=c(length(ajout[,1]),length(ajout[1,]),Ns) )  ,c(3,1,2))
      #  dim(ajout_Rdt_terme)
    #   dim(aperm(GSEpp[,Tp_deb:fin,D,],c(1,3,2)))
    #   dim(aperm( array(rep(ajout,Ns),dim=c(length(ajout[,1]),length(ajout[1,]),Ns) )  ,c(3,1,2)))
     }
    Rdt_terme[,,(Tp_deb):fin]<-ajout_Rdt_terme+Rdt_terme[,,Tp_deb:fin]
    
    # calcul pour les Ns trajectoire ds rendements pondere pour un investissement arretes a Tp
    ajout_Rdt_liquide<-array(0,dim= dim(ajout_Rdt_terme))
    for (j in (Tp_deb:fin)) {
      if (D==1) {
        ajout_Rdt_liquide[,]<-GSEpp[,j,j-Tp_deb+1,] * aperm(array(rep(ajout[,j-Tp_deb+1],Ns),dim=c(Nb_plac,Ns)),c(2,1))
      } else {
        ajout_Rdt_liquide[,,j-Tp_deb+1]<-GSEpp[,j,j-Tp_deb+1,] * aperm(array(rep(ajout[,j-Tp_deb+1],Ns),dim=c(Nb_plac,Ns)),c(2,1))
      } #fin boucle if
    } # fin boucle for
    Rdt_liquide[,,(Tp_deb):fin]<-ajout_Rdt_liquide+Rdt_liquide[,,(Tp_deb):fin]
    
  } # fin if
} # fin for 1:Nb_strip

# normalisation des % sur 1 eur
Mat_result_final<-Mat_result/aperm(array(rep(apply(Mat_result,2,sum),Nb_plac),dim=c(Horizon_max,Nb_plac)),c(2,1))
Mat_result_final[is.nan(Mat_result_final)]<-0
Mat_result_final[which(Mat_result_final<0.01)]<-0
Mat_result_final<-Mat_result_final/aperm(array(rep(apply(Mat_result_final,2,sum),Nb_plac),dim=c(Horizon_max,Nb_plac)),c(2,1))
# apply(Mat_result_final,2,sum)
# result sur sum_cuml
Mat_result_final<-Mat_result_final*aperm(array(rep(as.matrix(sum_cuml[1:Horizon_max]),Nb_plac),dim=c(Horizon_max,Nb_plac)),c(2,1))

Rdt_terme<-Rdt_terme/aperm(array(rep(apply(Mat_result,2,sum),Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))
Rdt_terme[is.nan(Rdt_terme)]<-0
# Rdt_terme[which(Rdt_terme<0.005)]<-0
Rdt_terme<-Rdt_terme*aperm(array(rep(as.matrix(sum_cuml[1:Horizon_max]),Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))

Rdt_liquide<-Rdt_liquide/aperm(array(rep(apply(Mat_result,2,sum),Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))
Rdt_liquide[is.nan(Rdt_liquide)]<-0
# Rdt_liquide[which(Rdt_liquide<0.005)]<-0
Rdt_liquide<-Rdt_liquide*aperm(array(rep(as.matrix(sum_cuml[1:Horizon_max]),Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))


return( list(Mat_result_final,Rdt_liquide,Rdt_terme) )

}