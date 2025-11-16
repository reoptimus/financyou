#########################
#
# Assemblage invest
#
# assemblage des investissements
# utilise d'un cote la liste de strip et de l'autre les resultats des placements optimum par Horizon
#
# cre le 13/10/2020
# par Sébastien Gallet
#
########################

Assembl_invest<-function(reptravail,pas_t,Avers,titre,seuil_filtre,nom_graph,list_placements,soltot,GSEpp,tabl_eur_cont,nom_client,pas_E){
  
# Variable interne à mettre en fonction
# reptravail<-"E:/R_Financyou"
# Avers<-5
# pas_t<-0.5 # pas de temps de presentation des resultats
# seuil_filtre<-0.02 # seuil filtre pour la visualisation des poches de placements
# nom_graph<-"test2"
# list_placements<-list_placements_opti
# pas_E<-10000

# chargement des strip
load(paste0(reptravail,"/MOCA/OUT/Strip_invest.Rda"))

# definition des variables internes
Nb_plac<-length(list_placements)
Horizon_max<-dim(soltot)[2] # en pas_t
Nb_Aversion<-dim(soltot)[4]
Nb_strip<-dim(Tr1)[1] # les données sont 1:debut, 2:fin, 3: le capital au moment de l'invest
Ns<-dim(GSEpp)[1] # Nb de scenario
#+ avec BoostrapV4, soltot ne depend pas de Tp et Tp=1 (les contraintes sont 0 sur les engagements)
#Tp<-dim(soltot)[3] # sinon Tp dans la boucle et Tp=Mat_strip[i,1]

Mat_result<-array(0,dim=c(Nb_plac,Horizon_max))
Rdt_terme<-array(0,dim=c(Ns,Nb_plac,Horizon_max))
Rdt_liquide<-array(0,dim=c(Ns,Nb_plac,Horizon_max))
Mat_strip<-floor(Tr1[,1:2])
Mat_strip[,2]<-(Mat_strip[,2]-Mat_strip[,1]) 
  
for (i in 1:Nb_strip) {
  if (Mat_strip[i,2]!=0) {
  Tp_deb=Mat_strip[i,1] # debut de l'investissement
  ajout<-array(rep(soltot[,Mat_strip[i,2],Tp_deb,Avers],Mat_strip[i,2]),dim=c(Nb_plac,Mat_strip[i,2]))
  Mat_result[,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1)]<-ajout+Mat_result[,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1)]
  # dim(ajout) # plac X D
  
  # calcul pour les Ns trajectoire ds rendements ponderes pour un investissement a terme
  if (length(dim(GSEpp[,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1),Mat_strip[i,2],]))!=3) { # cas D=1, la dim change
    ajout_Rdt_terme<-GSEpp[,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1),Mat_strip[i,2],] * aperm( array(rep(ajout,Ns),dim=c(length(ajout[,1]),length(ajout[1,]),Ns))  ,c(3,1,2))[,,1]
    } else {
    ajout_Rdt_terme<-aperm(GSEpp[,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1),Mat_strip[i,2],],c(1,3,2)) * aperm( array(rep(ajout,Ns),dim=c(length(ajout[,1]),length(ajout[1,]),Ns))  ,c(3,1,2))
    }
  Rdt_terme[,,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1)]<-ajout_Rdt_terme+Rdt_terme[,,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1)]

  # calcul pour les Ns trajectoire ds rendements pondere pour un investissement arretes à Tp
  ajout_Rdt_liquide<-array(0,dim= dim(ajout_Rdt_terme))
      for (j in ((Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1))) {
        if (Mat_strip[i,2]==1) {
          ajout_Rdt_liquide[,]<-GSEpp[,j,j-Mat_strip[i,1]+1,] * aperm(array(rep(ajout[,j-Mat_strip[i,1]+1],Ns),dim=c(Nb_plac,Ns)),c(2,1))
        } else {
          ajout_Rdt_liquide[,,j-Mat_strip[i,1]+1]<-GSEpp[,j,j-Mat_strip[i,1]+1,] * aperm(array(rep(ajout[,j-Mat_strip[i,1]+1],Ns),dim=c(Nb_plac,Ns)),c(2,1))
        }
      }
  Rdt_liquide[,,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1)]<-ajout_Rdt_liquide+Rdt_liquide[,,(Mat_strip[i,1]):(Mat_strip[i,1]+Mat_strip[i,2]-1)]
  
  } # fin if
} # fin for 1:Nb_strip
  
 # apply(Mat_result,2,sum)
 # dim(Rdt_terme)
 # dim(Rdt_liquide)
 # apply(Rdt_terme,2,sum)
 # apply(Rdt_liquide,2,sum)

Mat_result<-Mat_result*pas_E
Rdt_terme<-Rdt_terme*pas_E
Rdt_liquide<-Rdt_liquide*pas_E

# ajout des engagements du client
Mat_result<-Mat_result+tabl_eur_cont[list_prise,1:length(Mat_result[1,])]
# nettoyage des valeurs trop petite
Mat_result[which(abs(Mat_result)<0.02*pas_E,arr.ind=1)]<-0 # limite de 100 eur

save(Mat_result,Rdt_terme,Rdt_liquide,file=paste0(reptravail,"/MOCA/OUT/","Mat_result_",nom_client,".Rda"))
#plot(apply(Mat_result,2,sum),ylim=c(0,100))


rm(list=ls())
gc()

}