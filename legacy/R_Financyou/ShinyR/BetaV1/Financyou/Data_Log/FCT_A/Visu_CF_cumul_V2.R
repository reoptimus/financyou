############################
#
# script pour former le graphique de visu des cash flow : flux et cumul
#
# 13/03/2020
############################

Visu_CF_cumul <- function(matrice,horiz){
  titre_a<-"Liquidités"
  titre_b<-"Dépenses"
  titre_c<-c("Principal crd habitation","Intérêts crd habitation")
  titre_d<-"impôts sur revenus"
  titre_e<-"Principal crd placements"
  titre_f<-"Intéréts crd placements"
  titre_cbis<-"Loyer"
  
  
  # matrice<-tab_chrono
  # horiz=20
  # definition du graphique plot_A
  a<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="Epargne libre hors projets")
  a$type<-"Liquidites disponibles"
  b<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="depenses hors projets")
  b$type<-"Depenses courantes"
  
  if ( sum(filter(matrice,sous.type_2=="Votre logement")[4:(horiz+3)])==0 &
       sum(matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer")!=0) ) { # locataire
    etat<-"locataire"
    c<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer")
    c$type<-"Loyer" } else { # proprio
      flux_princ<-matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2=="Votre logement")
      if ( flux_princ[4:(horiz+3)][1]==0 ) { # fini de payer
        etat<-"fini_payer"
        c<-flux_princ
      } else { #remb en cours
        etat<-"proprio"
        c<- matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2=="Votre logement")
        c<-bind_rows(c,matrice %>% filter(type=="plc",sous.type=="interet",sous.type_2=="Votre logement") )
        c$type<-c("Principal du credit habitation","Interets du credit habitation")
      }
      
    }
  d<- matrice%>% filter(type=="impots",sous.type=="IR",sous.type_2=="hors_projets")
  
  e<- d
  e$type<-"Principal des credits placements"
  e$sous.type<-""
  e$sous.type_2<-""
  e[4:(horiz+3)]<-matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2!="Votre logement") %>% 
    select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  sum_e<-sum(e[4:(horiz+3)])
  
  f<- e
  f$type<-"Interets des credits placements"
  f$sous.type<-""
  f$sous.type_2<-""
  f[4:(horiz+3)]<-matrice %>% filter(type=="plc",sous.type=="interet") %>% 
    select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  
  
  if (etat=="locataire") {
    if (sum_e==0) { a<-bind_rows(a,b,c,d)
    list_propre<-c(titre_a,titre_b,titre_cbis,titre_d)
    } else { a<-bind_rows(a,b,c,d,e,f)
    list_propre<-c(titre_a,titre_b,titre_cbis,titre_d,titre_e,titre_f)}
  }
  if (etat=="proprio") {
    if (sum_e==0) { a<-bind_rows(a,b,c,d)
    list_propre<-c(titre_a,titre_b,titre_c,titre_d)
    } else { a<-bind_rows(a,b,c,d,e,f)
    list_propre<-c(titre_a,titre_b,titre_c,titre_d,titre_e,titre_f)}
  }
  if (etat=="fini_payer") {
    if (sum_e==0) { a<-bind_rows(a,b,d)
    list_propre<-c(titre_a,titre_b,titre_d)
    } else { a<-bind_rows(a,b,d,e,f)
    list_propre<-c(titre_a,titre_b,titre_d,titre_e,titre_f)}
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