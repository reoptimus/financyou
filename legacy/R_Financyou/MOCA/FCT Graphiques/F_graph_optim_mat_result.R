#' Fonction de mise en forme graphique des resultats d'optim
#' utilise la retour de Script_Boostrap.R
#' @param soltoti,Recap_tables_cumul,H
#' Mat_result
#' Recap_tables_cumul size matrice (names)
#' Aversion size list des coef d'aversion

Graph_optim<-function(soltoti,Recap_tables_cumul,titre,seuil_filtre,nom_graph){

  # donnes test
  # soltoti<-Mat_result
  # Recap_tables_cumul<-list_placements
  # seuil_filtre<-0.05
  # titre<-"test"
  # dim(soltot)

  #plot 2D

  NbTable<-length(Recap_tables_cumul)
  rownames(soltoti) <- Recap_tables_cumul

H<-dim(soltoti)[2]
datafrsoltot<-as.data.frame(soltoti[,])
colnames(datafrsoltot)<-1:H
apply(datafrsoltot,2,sum)

#filtrage des petites parts
comptage<-array(1,dim=c(NbTable,H))
rownames(comptage) <- Recap_tables_cumul
comptage[which(datafrsoltot<seuil_filtre, arr.ind = 1)]<-0
datafrsoltot[which(datafrsoltot<seuil_filtre, arr.ind = 1)]<-0

comptage<-comptage/aperm(array(rep(apply(datafrsoltot,2,sum),NbTable),dim=c(H,NbTable)),c(2,1))
datafrsoltot<-datafrsoltot*comptage
datafrsoltot<-datafrsoltot*aperm(array(rep(apply(soltoti,2,sum),NbTable),dim=c(H,NbTable)),c(2,1))
maxi<-max(apply(datafrsoltot[,2:H],2,sum))
#passage en % pour le graphique
#datafrsoltot<-datafrsoltot*100

#variables internes
xnames<-1:H
 
pdf(paste0(reptravail,"/MOCA/OUT/",nom_graph,".pdf"))
######### solution 1
barplot(as.matrix(datafrsoltot[,2:H]),beside=F,
       main=titre,
       xlab="Annees d investissement", ylab="Parts / type d'invest.", col=rainbow(length(datafrsoltot[,1])-1),
       xlim=c(2,H),
       legend.text=TRUE,
       args.legend=list(x=10,y=maxi,bty = "y", cex=0.7))
#######
dev.off()

barplot(as.matrix(datafrsoltot[,2:H]),beside=F,
        main=titre,
        xlab="Annees d investissement", ylab="Parts / type d'invest.", col=rainbow(length(datafrsoltot[,1])-1),
        xlim=c(2,H),
        legend.text=TRUE,
        args.legend=list(x=10,y=maxi, cex=0.7))

}