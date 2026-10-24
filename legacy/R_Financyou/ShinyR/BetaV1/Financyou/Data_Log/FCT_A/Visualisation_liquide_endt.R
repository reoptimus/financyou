#################################################
# script pour la visualisation de l'endettement et de la liquidite
# fait le 08/06/2020
# modifie le 
# methode 
#################################################

Visu_liquide<- function (tab_chrono,limite_endt,projet="Y",list_placements_compl,Rdt_liqui) {
  # Rdt_liqui <- Rdt_liquide[1,,1]
  # limite_endt<-0.35
  
  if (projet=="Y") {
    endt<-tab_chrono %>% filter(type=="life", sous.type=="taux_endt",sous.type_2=="avec projets") %>% select(-type,-sous.type,-sous.type_2)
    liquide<- tab_chrono %>% filter(type=="life", sous.type=="hors_imp",sous.type_2=="Epargne libre avec projets") %>% select(-type,-sous.type,-sous.type_2)
    } else {
    endt<-tab_chrono %>% filter(type=="life", sous.type=="taux_endt",sous.type_2=="hors projets") %>% select(-type,-sous.type,-sous.type_2)
    liquide<- tab_chrono %>% filter(type=="life", sous.type=="hors_imp",sous.type_2=="Epargne libre hors projets") %>% select(-type,-sous.type,-sous.type_2)
  }
   taux_endettement<-t(endt)
   ####### ajout du capital liquide a t0 ####
   a<-intersect(list_placements_compl,as.character(table_invest$placements[table_invest$Liquide==1]))
   b<-c()
   if (is.integer0(a)==FALSE){
       for (i in 1:length(a)) {
         b<-c(b,which(list_placements_compl==a[i]))
       }
    liquide[1]<-liquide[1]-sum(Rdt_liqui[b])
   }
   ############
   
  horiz<-length(liquide)
  liquide<- -liquide
    for (i in 2:horiz) {
      liquide[,i]<-liquide[,i]+liquide[,(i-1)]
    }
  liquidite<-t(liquide)
 

p<- ggplot() + 
  geom_line(aes(x=1:horiz,y=liquidite),size=1, show.legend =FALSE)+
  theme_minimal() + # dark , minimal , void , light , classic , bw
  theme (legend.position = "right") + # left, right,top legend.background = "black",
   # "solid", "longdash", "dashed", "dotted"
  scale_x_discrete(name = NULL, labels = NULL) +
  scale_y_continuous(name = "Epargne \n disponible", 
                    labels = function(j) { paste0(round(j/1000, 0), "k€")}) + 
  theme(axis.title.y = element_text(color = "blue")) +
  geom_hline(yintercept=0 , color="red", size=1, linetype="longdash", show.legend =FALSE) +
  geom_ribbon( aes(1:horiz, ymin = apply( cbind( liquidite, rep(0,horiz) ),1,min ) , ymax = 0,alpha=0.5,fill="red"), show.legend =FALSE)

q<- ggplot() + 
  geom_line(aes(x=(1:horiz),y=taux_endettement), show.legend = FALSE, size=1) +
  theme_minimal() + # dark , minimal , void , light , classic , bw
  theme (legend.position = "right") +
  scale_x_discrete(name = "Année de projections", labels = NULL) +
  scale_y_continuous(name = "Taux\n d'endettement", limits=c(0,0.5), 
                     labels = function(j) { paste0(round(j*100, 0), "%")}) + 
  theme(axis.title.y = element_text(color = "blue")) +
  geom_hline( yintercept=limite_endt , color="red", size=1, linetype="longdash", show.legend =FALSE) +
  geom_ribbon( aes(1:horiz, ymin =limite_endt , ymax = apply( cbind( taux_endettement, rep(limite_endt,horiz) ),1,max) ,alpha=0.5,fill="red"), show.legend =FALSE)

r<-grid.arrange(p, q,ncol=1, nrow = 2)

# r <- ggplotly(r)  # ,tooltip = c("y", "x")

return(r)

#lines(x,mean,type="l",col="red")

} #fin de la fonction
