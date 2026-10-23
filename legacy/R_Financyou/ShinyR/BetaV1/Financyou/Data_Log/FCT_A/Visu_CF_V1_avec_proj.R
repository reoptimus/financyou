############################
#
# script pour former le graphique de visu des cash flow : flux et cumul
#
# 13/03/2020
############################

Visu_CF_avec_proj <- function(matrice,horiz){
  
  titre_a<-"Liquidités"
  titre_b<-"Dépenses"
  titre_c<-c("Principal crd habitation","Intérêts crd habitation")
  titre_d<-"impôts sur revenus"
  titre_e<-"Principal crd placements"
  titre_f<-"Intéréts crd placements"
  titre_cbis<-"Loyer"
  
  # matrice<-tab_chrono
  # definition du graphique plot_A
  a<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="Epargne libre avec projets")
  a$type<-"Liquidites disponibles"
  b<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="depenses avec projets")
  b$type<-"Depenses courantes"
  
  kro=0
  if ( sum(filter(matrice,sous.type_2=="Votre logement")[4:(horiz+3)])==0 ) { # locataire
  c<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer")
  kro=1
  c$type<-"Loyer" } else { # proprio
    kro=2
    c<- matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2=="Votre logement")
    c<-bind_rows(c,matrice %>% filter(type=="plc",sous.type=="interet",sous.type_2=="Votre logement") )
    c$type<-c("Principal du credit habitation","Interets du credit habitation")
  }
  
  d<- matrice%>% filter(type=="impots",sous.type=="IR",sous.type_2=="final")
  
  e<- matrice %>% filter(type=="plc"|type=="projets",sous.type=="principal",sous.type_2!="Votre logement") %>% 
    select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  e$type<-"Principal des credits placements"
  e$sous.type<-""
  e$sous.type_2<-""
  
  f<- matrice %>% filter(type=="plc",sous.type=="interet")
  fbis<- matrice %>% filter(type=="projets",sous.type=="hors_imp",sous.type_2=="immo")
  f<-bind_rows(f,fbis)
  f<- f %>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  f$type<-"Interets des credits placements"
  f$sous.type<-""
  f$sous.type_2<-""

  
  if (kro==1|kro==0) { #locataire ou proprio fini de payer
    a<-bind_rows(a,b,c,d) 
    list_propre<-c(titre_a,titre_b,titre_cbis,titre_d) 
     } else { 
    a<-bind_rows(a,b,c,d,e,f) 
    list_propre<-c(titre_a,titre_b,titre_c,titre_d,titre_e,titre_f)
    }
  # # revenu projets
  # g<- matrice %>% filter(type=="projets",sous.type=="revenu")%>% 
  #   select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # g<- -g
  # g$type<-"Impact sur les projets"
  # g$sous.type<-""
  # g$sous.type_2<-""
  # # depenses projets
  #   h<-matrice %>% filter(type=="projets",sous.type=="hors_imp")%>% 
  #     select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  #   h$type<-"flux des projets hors imp"
  #   h$sous.type<-""
  #   h$sous.type_2<-""
  #  
      # a<-bind_rows(a,g,h) 
      # list_propre<-c(list_propre,titre_g,titre_h) 

          #Verif
    # a1<-a %>% select(-"type",-"sous.type",-"sous.type_2") %>% summarise_all(sum)
    # a2<-matrice %>% filter(sous.type=="revenu") %>%
    #   select(-"type",-"sous.type",-"sous.type_2") %>%
    #   summarise_all(sum)
    # a1+a2
    
    a<- a %>% select(-"sous.type",-"sous.type_2")
  
  names(a)<-c("type de flux",seq(horiz))
  list_champ<-a$"type de flux"
  a<- a %>% select(-"type de flux")
  a<-as.data.frame(t(a),stringsAsFactors = FALSE)
  names(a)<-list_champ
  a$ans<-seq(horiz)
  
  a<-gather(a,key="ans")
  a$an<-rep(seq(horiz),length(unique(a[,"ans"])) )
  # changement de l'unite
  a$value<-round(-(a$value/1000),1) # en k eur
  list<-unique(a$ans)
  for (i in 1:length(list)) {
  a[which(a$ans==list[i]),1]<-list_propre[i]
  }
  
  p<-ggplot(a, aes(x=an,y=value, fill=ans)) + 
    # geom_area(alpha=0.6 , size=1, colour="black") +
    # theme_ipsum() +
    scale_fill_viridis(discrete = T) +
    geom_col( position = "stack", #"stack" "dodge"
      width = 0.5,
      na.rm = FALSE,
      show.legend = FALSE
    ) +
    #scale_fill_brewer (palette="Paired") + # "PuBuGn" "Blues"
    theme_minimal() + # dark , minimal , void , light , classic , bw
    labs(x="Années de projections",y="Flux en milliers d'Euro",title="", subtitle="",caption="FinancYou.com") +
    theme (legend.position = "right") #+ # left, right,top legend.background = "black",
  
  p<-ggplotly(p)
  
  return(p)
  #ggsave(file=paste0("Data_Log/plot_cash.png"), plot = p, device = NULL)
  # dev.off()
}
