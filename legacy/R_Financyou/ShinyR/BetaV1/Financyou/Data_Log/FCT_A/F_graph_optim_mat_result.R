#' Fonction de mise en forme graphique des resultats d'optim
#' utilise la retour de Script_Boostrap.R
#' param soltoti,List_actifsl,H
#' Mat_result
#' List_actifs size matrice (names)
#' Aversion size list des coef d'aversion

Graph_optim<-function(soltoti,List_actifsl,list_placements_compl){

  # donnes test
  # soltoti<-Mat_result_proj
  # List_actifsl<-list_placements_proj
  # dim(soltoti) # str(soltoti)
  
  NbTable<-dim(List_actifsl)[[1]]
  H<-dim(soltoti)[2]
  datafrsoltot<-as.data.frame(soltoti[,])
  colnames(datafrsoltot)<-1:H
  # apply(datafrsoltot,2,sum)
  
  # mise en forme des titres des placements
  list_titres_plc_compl<-c("Action PEA","Comptes et livrets","Assurance Vie Eur","Assurance Vie UC","Immo Locatif","Habitation propre","Immo Pinel","Résidence secondaire","Crédit immo locatif","Crédit Habitation","Crédit Pinel","Crédit résid.secondaire")
  List_actifs<-list_titres_plc_compl[match( as.character(List_actifsl[,1]) ,list_placements_compl[[2]])]

  #variables internes
  xnames<-1:H
  datatest<-cbind(List_actifs,datafrsoltot)
  datatest<-as.data.table(datatest) # setDT(datatest)
  datatest<-suppressWarnings(melt(datatest))
  colnames(datatest)<-c("actifs","an","montant")
  
  datatest$montant<-round(datatest$montant/1000,1)
  ordre_levels<-list_titres_plc_compl
  ordre_levels<- ordre_levels[c(5,9,6,10,7,11,8,12,1:4)]
  
  # mise en ordre de la legende
  order_actifs<-c()
  liste<-levels(unique(datatest$actifs))
  for (i in 1:length(ordre_levels) ) {
    if (sum(liste==ordre_levels[i])==TRUE) { # trouve
      order_actifs<-c(order_actifs,liste[which(liste==ordre_levels[i])] )
    } else {}#pas trouve
  }
  
  datatest$actifs<- factor(datatest$actifs , levels=rev(order_actifs))
  
  p<- ggplot(data = datatest, aes(x=an,y=montant, fill=actifs)) + 
    # geom_area(alpha=0.6 , size=1, colour="black") +
    # theme_ipsum() +
    # scale_fill_viridis(discrete = T) +
    geom_col( position = "stack", #"stack" "dodge"
              width = 0.5,
              na.rm = FALSE,
              show.legend = FALSE
    ) +
    scale_fill_brewer (palette="Paired") + # "PuBuGn" "Blues"
    theme_minimal() + # dark , minimal , void , light , classic , bw
    labs(x="Annees de projections",y="Epargne \n en milliers Eur",title="", subtitle="",caption="FinancYou.com") +
    theme (legend.position = "right") #+ # left, right,top legend.background = "black",

  p<- ggplotly(p)
  
  return(p)
  
}