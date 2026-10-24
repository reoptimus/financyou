############################
#
# script pour former le graphique de visu des cash flow : flux et cumul
#
# 13/03/2020
############################

Visu_CF_proj <- function(matrice_flux){
  # matrice_flux<-a_plot
  # definition du graphique plot_A
  matrice<-cbind(seq(length(matrice_flux[,1])), matrice_flux )
  colnames(matrice)[1]<-"ans"
  #matrice$revenu<-NULL
  
  a<-gather(matrice[,-2], type, value,-ans) #on retire la 2ieme colonne "test"
  # changement de l'unite
  # a$value<-a$value/1000 # en k eur
  
  p<-ggplot(a, aes(x=ans,y=value, fill=type)) + 
    # geom_area(alpha=0.6 , size=1, colour="black") +
    # #scale_fill_viridis(discrete = TRUE) +
    # scale_fill_brewer (palette="Blues") +
    # #theme_ipsum() +
    # theme (legend.position = "bottom",legend.title = element_blank(),legend.justification = "center",legend.direction = "vertical") +
    # labs(x="",y="",title=NULL, subtitle="",caption="exemple caption")
    # ggtitle("The race between ...")
    geom_col( position = "dodge", #"stack"
      width = 1,
      na.rm = FALSE,
      show.legend = FALSE
    ) +
    #scale_fill_brewer (palette="Blues") + # "PuBuGn" "Blues"
    theme_light() + # dark , minimal , void , light , classic , bw
    #scale_fill_viridis(discrete = T) +
    labs(x="Annees de projections",y="Flux en milliers d'Euro",title="", subtitle="",caption="exemple caption") +
    theme (legend.position = "bottom") # left, right,top legend.background = "black",
  
  p<-ggplotly(p)
  
  return(p)
  #ggsave(file=paste0("Data_Log/plot_cash.png"), plot = p, device = NULL)
  # dev.off()
}