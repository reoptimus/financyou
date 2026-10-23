############################
#
# script pour former le graphique de visu des cash flow : flux et cumul
#
# 13/03/2020
############################

Visu_CF_cumul <- function(matrice,horiz){
  # matrice<-tab_chrono
  # definition du graphique plot_A
  a<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="Epargne libre hors projets")
  a$type<-"Liquidites disponibles"
 
  if ( sum(filter(matrice,sous.type_2=="Votre logement")[4:(horiz+3)])==0 ) { # locataire
    locataire<-1
   } else { # proprio
     locataire<-0
    c<- matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2=="Votre logement")
    c$type<-"Principal du credit habitation"
    }
 
  e<- matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2!="Votre logement") %>% 
    select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  sum_e<-sum(e)
  e$type<-"Principal des credits placements"
  e$sous.type<-""
  e$sous.type_2<-""
  
  if (locataire==1) { # locataire
    if (sum_e==0) {a<-bind_rows(a)} else { a<-bind_rows(a,e) }
  } else { # proprio
    if (sum_e==0) {a<-bind_rows(a,c)} else { a<-bind_rows(a,c,e) }
  }
  
  
  # verification
  # som_revenu<-matrice %>% filter(type!="projets",sous.type=="revenu") %>% select(-"sous.type",-"sous.type_2",-"type")
  # som_revenu<-apply(som_revenu,2,sum)
  # som_revenu+apply(a %>% select(-"sous.type",-"sous.type_2",-"type"),2,sum)
  
    a<- a %>% select(-"sous.type",-"sous.type_2")
    a<- a %>% filter(type!="impots",type!="Interets du credit habitation",type!="Interets des credits placements",type!="Depenses courantes")
  
  names(a)<-c("type de flux",seq(horiz))
  list_champ<-a$"type de flux"
  a<- a %>% select(-"type de flux")
  a<-as.data.frame(t(a),stringsAsFactors = FALSE)
  names(a)<-list_champ
  a$ans<-seq(horiz)
  
  ##### CUMUL #####
  # forme finale avant graph
  a_cumul<-a
  for (i in 2:length(a_cumul$ans)) {
    a_cumul[i,]<-a_cumul[i-1,]+a_cumul[i,]
  }
  a_cumul$ans<-seq(horiz)
  a<-a_cumul
  #################

  
  a<-gather(a,key="ans")
  a$an<-rep(seq(horiz),length(unique(a[,"ans"])) )
  # changement de l'unite
  a$value<-round(abs(a$value/1000),1) # en k eur
  

  p<-ggplot(a, aes(x=an,y=value, fill=ans)) + 
    # geom_area(alpha=0.6 , size=1, colour="black") +
    # theme_ipsum() +
    # scale_fill_viridis(discrete = T,option="C") +
    geom_area( position = "stack", #"stack" "dodge"
      #width = 0.5,
      na.rm = FALSE,
      show.legend = FALSE
    ) +
     scale_fill_brewer (palette="Paired") + # "PuBuGn" "Blues"
    theme_minimal() + # dark , minimal , void , light , classic , bw
    labs(x="Annees de projections",y="Flux en milliers d'Euro",title="", subtitle="",caption="FinancYou.com") +
    theme (legend.position = "right") #+ # left, right,top legend.background = "black",
    #geom_line(data=suma, aes(x=an,y=Revenu,fill=NULL),colour="darkblue", size=5, alpha=0.4)
  
  p<-ggplotly(p)
  
  return(p)
  #ggsave(file=paste0("Data_Log/plot_cash.png"), plot = p, device = NULL)
  # dev.off()
}