############################
#
# script pour former le graphique de visu des cash flow : flux et cumul
#
# 13/03/2020
############################

Visu_CF_plc <- function(matrice_flux1,matrice_flux2){

  #####################################
  matrice_flux<-matrice_flux1
  matrice_flux<-as.data.frame(matrice_flux)
  matrice_flux<-cbind(matrice_flux,rownames(matrice_flux))
  names(matrice_flux)<-c("count","category")  
  # matrice_flux[,2]<-c("plc1","plc2","plc3")
  # Compute percentages
  matrice_flux$fraction <- matrice_flux$count / sum(matrice_flux$count)
  # Compute the cumulative percentages (top of each rectangle)
  matrice_flux$ymax <- cumsum(matrice_flux$fraction)
  # Compute the bottom of each rectangle
  matrice_flux$ymin <- c(0, head(matrice_flux$ymax, n=-1))
  # Compute label position
  matrice_flux$labelPosition <- (matrice_flux$ymax + matrice_flux$ymin) / 2
  # Compute a good label
  matrice_flux$label <- paste0(matrice_flux$category, "\n ", round(matrice_flux$count,0),"eur" , "\n ", round(matrice_flux$fraction*100,0),"%")
  # Make the plot
  p1<-ggplot(matrice_flux, aes(ymax=ymax, ymin=ymin, xmax=4, xmin=3, fill=category)) +
    geom_rect() +
    geom_label_repel(x=3.5, aes(y=labelPosition, label=label), size=3.5, colour="black", segment.colour="black") +
    scale_fill_brewer(palette=1) +
    coord_polar(theta="y") +
    xlim(c(2, 4)) +
    theme_void() +
    theme(legend.position = "none",plot.title = element_text(color="Blue", size=14, face="bold.italic") ) +
    ggtitle("Valeur Brut du patrimoine")

  #####################################
  matrice_flux<-matrice_flux2
  matrice_flux<-as.data.frame(matrice_flux)
  matrice_flux<-cbind(matrice_flux,rownames(matrice_flux))
  names(matrice_flux)<-c("count","category")  
  # matrice_flux[,2]<-c("plc1","plc2","plc3")
  # Compute percentages
  matrice_flux$fraction <- matrice_flux$count / sum(matrice_flux$count)
  # Compute the cumulative percentages (top of each rectangle)
  matrice_flux$ymax <- cumsum(matrice_flux$fraction)
  # Compute the bottom of each rectangle
  matrice_flux$ymin <- c(0, head(matrice_flux$ymax, n=-1))
  # Compute label position
  matrice_flux$labelPosition <- (matrice_flux$ymax + matrice_flux$ymin) / 2
  # Compute a good label
  matrice_flux$label <- paste0(matrice_flux$category, "\n ", round(matrice_flux$count,0),"eur" , "\n ", round(matrice_flux$fraction*100,0),"%")
  # Make the plot
  p2<-ggplot(matrice_flux, aes(ymax=ymax, ymin=ymin, xmax=4, xmin=3, fill=category)) +
    geom_rect() +
    geom_label_repel(x=3.5, aes(y=labelPosition, label=label), size=3.5, colour="black", segment.colour="black") +
    scale_fill_brewer(palette=2) +
    coord_polar(theta="y") +
    xlim(c(2, 4)) +
    theme_void() +
    theme(legend.position = "none", plot.title = element_text(color="Green", size=14, face="bold.italic") ) +
    ggtitle("Valeur hors crédits en cours")
  
  #####################################
  p<-grid.arrange(p1, p2, nrow=2)
  return(p)

  #ggsave(file=paste0("Data_Log/plot_cash.png"), plot = p, device = NULL)
  # dev.off()
}