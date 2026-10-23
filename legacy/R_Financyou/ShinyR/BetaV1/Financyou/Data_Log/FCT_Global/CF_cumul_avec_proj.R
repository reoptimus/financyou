############################
#
# script pour former le graphique de visu des cash flow : flux et cumul
#
# modifie le 09/06/2020
# par sebastien gallet
# financyou.com
############################

CF_avec_proj <- function(matrice,horiz,projet="Y"){

  # projet= Y : avec projet, sans sinon
  
  # matrice<-tab_chrono
  # definition du graphique plot_A
  if (projet=="Y") {
    a<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="Epargne libre avec projets")
    b<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="depenses avec projets")
    d<- matrice%>% filter(type=="impots",sous.type=="IR",sous.type_2=="final")
    e<- matrice %>% filter(sous.type=="principal",sous.type_2!="Votre logement") %>% #type=="plc"&"projets"
      select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
    g<- matrice %>% filter(type=="projets",sous.type=="hors_imp") %>% 
      select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
    g$type<-"Depenses projets hors impots"
    g$sous.type<-""
    g$sous.type_2<-""
  } else {
    a<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="Epargne libre hors projets")
    b<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="depenses hors projets")
    d<- matrice%>% filter(type=="impots",sous.type=="IR",sous.type_2=="hors_projets")
    e<- matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2!="Votre logement") %>% #type=="plc"&"projets"
      select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  }
  a$type<-"Liquidites disponibles"
  b$type<-"Depenses courantes"
  
  if ( sum(filter(matrice,sous.type_2=="Votre logement")[4:(horiz+3)])==0 ) { # locataire
    c<- matrice %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer")
    c$type<-"Loyer" } else { # proprio
      c<- matrice %>% filter(type=="plc",sous.type=="principal",sous.type_2=="Votre logement")
      c<-bind_rows(c,matrice %>% filter(type=="plc",sous.type=="interet",sous.type_2=="Votre logement") )
      c$type<-c("Principal du credit habitation","Interets du credit habitation")
    }
  
  sum_e<-sum(e)
  e$type<-"Principal des credits placements"
  e$sous.type<-""
  e$sous.type_2<-""
  
  f<- matrice %>% filter(type=="plc",sous.type=="interet",sous.type_2!="Votre logement") %>% 
    select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  f$type<-"Interets des credits placements"
  f$sous.type<-""
  f$sous.type_2<-""
  
  
  if (projet=="Y") {
      if (sum_e==0) {
        a<-bind_rows(a,b,c,d,g) 
      } else { 
        a<-bind_rows(a,b,c,d,e,f,g) 
      }
  } else {
    if (sum_e==0) {
      a<-bind_rows(a,b,c,d) 
    } else { 
      a<-bind_rows(a,b,c,d,e,f) 
    }
  }
  #Verif
  # a1<-a %>% select(-"type",-"sous.type",-"sous.type_2") %>% summarise_all(sum)
  # a2<-matrice %>% filter(sous.type=="revenu") %>%
  #   select(-"type",-"sous.type",-"sous.type_2") %>%
  #   summarise_all(sum)
  # a1+a2
  
  a<- a %>% select(-"sous.type",-"sous.type_2")
  
  ##### CUMUL #####
  # forme finale avant graph
  for (i in 3:length(a[1,])) {
    a[,i]<-a[,i-1]+a[,i]
  }
  
  return(a)
  #ggsave(file=paste0("Data_Log/plot_cash.png"), plot = p, device = NULL)
  # dev.off()
}