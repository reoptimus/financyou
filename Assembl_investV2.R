#########################
#
# Assemblage invest
#
# assemblage des investissements
# utilise d'un cote la liste de strip et de l'autre les resultats des placements optimum par Horizon
#
# Version 2 : integration de la partie contrainte (emprunt à soltot)
# modifiee le 21/20/2020
# par Sébastien Gallet
#
########################

Assembl_invest<-function(reptravail,pas_t,Avers,titre,seuil_filtre,nom_graph,list_placements,soltot,GSEpp,tabl_pourc_conti,nom_client){
  
# Variable interne à mettre en fonction
# reptravail<-"E:/R_Financyou"
# Avers<-5
# pas_t<-0.5 # pas de temps de presentation des resultats
# seuil_filtre<-0.02 # seuil filtre pour la visualisation des poches de placements
# nom_graph<-"test2"
# list_placements<-list_placements_opti
# pas_E<-10000
# tabl_pourc_conti<-tabl_pourc_cont0
# GSEpp<-GSEpp_cuml

# chargement des strip
load(paste0(reptravail,"/MOCA/OUT/Strip_invest.Rda"))

# definition des variables internes
Nb_plac<-length(list_placements)
Horizon_max<-dim(soltot)[2] # en pas_t
Nb_Aversion<-dim(soltot)[4]
Nb_strip<-dim(Tr1)[1] # les données sont 1:debut, 2:fin, 3: le capital au moment de l'invest
Ns<-dim(GSEpp)[1] # Nb de scenario

Mat_result<-array(0,dim=c(Nb_plac,Horizon_max))
Rdt_terme<-array(0,dim=c(Ns,Nb_plac,Horizon_max))
Rdt_liquide<-array(0,dim=c(Ns,Nb_plac,Horizon_max))
Mat_strip<-floor(Tr1[,1:2])
Mat_strip[,2]<-(Mat_strip[,2]-Mat_strip[,1]) 

i=1
for (i in 1:Nb_strip) { # boucle sur les strip
  Tp_deb=Mat_strip[i,1] # debut de l'investissement
  D=Mat_strip[i,2]
  
  if (D!=0) {
  
  # tranche de placement en pourcent: debut: Tp_debut , fin: Tp_debut+D-1 , pour tabl_pourc_cont0 avec renormalisation
  ajout<-array(rep(soltot[,D,Tp_deb,Avers],D),dim=c(Nb_plac,D))
  
  # apply(ajout,2,sum)
  if (D==1) {
    ajout<-ajout*(1-sum(tabl_pourc_conti[,Tp_deb:(Tp_deb+D-1)]))
  }else {
    ajout<-ajout*(1-aperm(array(rep(apply(tabl_pourc_conti[,Tp_deb:(Tp_deb+D-1)],2,sum),Nb_plac),dim=c(D,Nb_plac)),c(2,1)))
  }
  ajout<-(ajout+tabl_pourc_conti[,Tp_deb:(Tp_deb+D-1)]) # ajout de la contrainte exterieure et normalisation
  
  # apply(ajout,2,sum)==1
  Mat_result[,(Tp_deb):(Tp_deb+D-1)]<-ajout+Mat_result[,(Tp_deb):(Tp_deb+D-1)]
  
  # calcul pour les Ns trajectoire ds rendements ponderes pour un investissement a terme
  if (length(dim(GSEpp[,(Tp_deb):(Tp_deb+D-1),D,]))!=3) { # cas D=1, la dim change
    ajout_Rdt_terme<-GSEpp[,(Tp_deb):(Tp_deb+D-1),D,] * aperm( array(rep(ajout,Ns),dim=c(length(ajout[,1]),length(ajout[1,]),Ns))  ,c(3,1,2))[,,1]
    } else {
    ajout_Rdt_terme<-aperm(GSEpp[,(Tp_deb):(Tp_deb+D-1),D,],c(1,3,2)) * aperm( array(rep(ajout,Ns),dim=c(length(ajout[,1]),length(ajout[1,]),Ns))  ,c(3,1,2))
    }
  Rdt_terme[,,(Tp_deb):(Tp_deb+D-1)]<-ajout_Rdt_terme+Rdt_terme[,,(Tp_deb):(Tp_deb+D-1)]

  # calcul pour les Ns trajectoire ds rendements pondere pour un investissement arretes à Tp
  ajout_Rdt_liquide<-array(0,dim= dim(ajout_Rdt_terme))
      for (j in ((Tp_deb):(Tp_deb+D-1))) {
        if (D==1) {
          ajout_Rdt_liquide[,]<-GSEpp[,j,j-Tp_deb+1,] * aperm(array(rep(ajout[,j-Tp_deb+1],Ns),dim=c(Nb_plac,Ns)),c(2,1))
        } else {
          ajout_Rdt_liquide[,,j-Tp_deb+1]<-GSEpp[,j,j-Tp_deb+1,] * aperm(array(rep(ajout[,j-Tp_deb+1],Ns),dim=c(Nb_plac,Ns)),c(2,1))
        } #fin boucle if
      } # fin boucle for
  Rdt_liquide[,,(Tp_deb):(Tp_deb+D-1)]<-ajout_Rdt_liquide+Rdt_liquide[,,(Tp_deb):(Tp_deb+D-1)]
  
  } # fin if
} # fin for 1:Nb_strip
  
 # apply(Mat_result_final,2,sum)
 # dim(Rdt_terme)
dim(GSEpp)
 # dim(Rdt_liquide)
 # apply(Rdt_liquide,2,sum)
 # apply(apply(Rdt_liquide,c(2,3),mean),2,sum)
apply(apply(GSEpp[,1,,],c(2,3),mean),2,sum)

# ajout des contraintes et rendements exterieurs
# normalisation des % sur 1 eur
Mat_result_final<-Mat_result/aperm(array(rep(apply(Mat_result,2,sum),Nb_plac),dim=c(Horizon_max,Nb_plac)),c(2,1))
# result sur sum_cuml
Mat_result_final<-Mat_result_final*aperm(array(rep(sum_cuml[1:Horizon_max],Nb_plac),dim=c(Horizon_max,Nb_plac)),c(2,1))

Rdt_terme<-Rdt_terme/aperm(array(rep(apply(Mat_result,2,sum),Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))
Rdt_terme<-Rdt_terme*aperm(array(rep(sum_cuml[1:Horizon_max],Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))

Rdt_liquide<-Rdt_liquide/aperm(array(rep(apply(Mat_result,2,sum),Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))
Rdt_liquide<-Rdt_liquide*aperm(array(rep(sum_cuml[1:Horizon_max],Nb_plac,Ns),dim=c(Horizon_max,Nb_plac,Ns)),c(3,2,1))

# nettoyage des valeurs trop petite
#Mat_result_final[which(abs(Mat_result)<0.02*pas_E,arr.ind=1)]<-0 # limite de materialite comptable
Mat_result<-Mat_result_final

save(Mat_result,Rdt_terme,Rdt_liquide,file=paste0(reptravail,"/MOCA/OUT/","Mat_result_",nom_client,".Rda"))
#plot(apply(Mat_result,2,sum),ylim=c(0,100))


rm(list=ls())
gc()

}