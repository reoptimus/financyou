#' Fonction de mise en forme graphique des resultats d'optim
#' utilise la retour de Script_Boostrap.R
#' @param soltoti,Recap_tables_cumul,H
#' soltoti size matrice [nb_Invest,T,nb_Aversion]
#' Recap_tables_cumul size matrice (names)
#' Aversion size list des coef d'aversion

Graph_optim<-function(soltoti,Recap_tables_cumul,titre,Aversion,seuil_filtre){

  # donnes test
  # soltoti<-soltot
  # Recap_tables_cumul<-list_placements
  # Aversion<-4
  # seuil_filtre<-0.05
  # titre<-"test"
  
  #plot 2D

  NbTable<-length(Recap_tables_cumul)
  rownames(soltoti) <- Recap_tables_cumul

H<-dim(soltoti)[2]
datafrsoltot<-as.data.frame(soltoti[,,Aversion])
colnames(datafrsoltot)<-1:H
apply(datafrsoltot,2,sum)

#filtrage des petites parts
comptage<-array(1,dim=c(NbTable,H))
rownames(comptage) <- Recap_tables_cumul
comptage[which(datafrsoltot<seuil_filtre, arr.ind = 1)]<-0
datafrsoltot[which(datafrsoltot<seuil_filtre, arr.ind = 1)]<-0

comptage<-comptage/aperm(array(rep(apply(datafrsoltot,2,sum),NbTable),dim=c(H,NbTable)),c(2,1))
datafrsoltot<-datafrsoltot*comptage
apply(datafrsoltot,2,sum)

#passage en % pour le graphique
#datafrsoltot<-datafrsoltot*100

#variables internes
xnames<-1:H

#######
# p <- plot_ly(datafrsoltot, x = xnames, y = datafrsoltot, name = rownames(datafrsoltot), type = 'scatter', mode = 'none', fill = 'tozeroy', fillcolor = listcolor[4])%>%
#   # add_trace(y = datafrsoltot[,3], name = colnames(datafrsoltot)[3], fillcolor = listcolor[3])%>%
#   # add_trace(y = datafrsoltot[,2], name = colnames(datafrsoltot)[2], fillcolor = listcolor[2])%>%
#   # add_trace(y = datafrsoltot[,1], name = colnames(datafrsoltot)[1], fillcolor = listcolor[1])%>%
#   layout(title = c("Repartition du portefeuille reoptimus",paste(" Aversion = ",Aversion, " ans")),
#          xaxis = list(title = "Niveaux de risques",
#                       showgrid = FALSE),
#          yaxis = list(title = "Parts / type d'invest.",
#                       showgrid = FALSE,
#                       ticksuffix = '%'),
#          legend = list(orientation = 'h'))
# p
 
######### solution Bis
barplot(as.matrix(datafrsoltot[,2:H]),
       main=titre,
       xlab="Annees d investissement", ylab="Parts / type d'invest.", col=rainbow(length(datafrsoltot[,1])-1),
       xlim=c(2,H),
       legend.text=TRUE,
       args.legend=list(x=20,y=0.7,bty = "y", cex=0.7))
#######

#rm(datafrsoltot,listcolor,xnames)
#gc()
}