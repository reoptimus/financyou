#
# fonction pour mettre en forme les KPI
#
# cree le 12/06/2020
# par sebastien gallet
# financyou.com
#############################

KPI<-function(tab_chrono,num=1,proj="Y"){
  # num des KPI
  # 1 : somme des revenu
  # 2 : somme des depenses
  # 3 : somme des impots
  # 4 : max du taux d endettement
  # 5 : min liquididte
  numer<-0
  if (num==1) {
    if (proj=="N") {
      numer<-sum(tab_chrono %>% filter(sous.type=="revenu",type!="projets")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    } else {
      numer<-sum(tab_chrono %>% filter(sous.type=="revenu")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    }
    b<-"eur"
    }
  if (num==2) {
    if (proj=="N") {
      numer<--sum(tab_chrono %>% filter(sous.type_2=="depenses hors projets",sous.type=="hors_imp",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    } else {
      numer<--sum(tab_chrono %>% filter(sous.type_2=="depenses avec projets",sous.type=="hors_imp",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    }
    b<-"eur"
  }
  if (num==3) {
    if (proj=="N") {
      numer<--sum(tab_chrono %>% filter(sous.type_2=="hors_projets",sous.type=="IR",type=="impots")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    } else {
      numer<--sum(tab_chrono %>% filter(sous.type_2=="final",sous.type=="IR",type=="impots")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    }
    b<-"eur"
  }
  if (num==4) {
    if (proj=="N") {
      numer<-100*max(tab_chrono %>% filter(sous.type_2=="hors projets",sous.type=="taux_endt",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    } else {
      numer<-100*max(tab_chrono %>% filter(sous.type_2=="avec projets",sous.type=="taux_endt",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
    }
    b<-"%"
  }
  if (num==5) {
    if (proj=="N") {
      numer<-(tab_chrono %>% filter(sous.type_2=="Epargne libre hors projets",sous.type=="hors_imp",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
      
      } else {
      numer<-min(tab_chrono %>% filter(sous.type_2=="Epargne libre avec projets",sous.type=="hors_imp",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum))
      }
    for (i in 2:length(numer)){numer[i]<-numer[i-1]+numer[i]}
    numer<--min(numer)
    b<-"eur"
  }
  
retun<-format(round(numer,0),big.mark = " ")
# passage en texte
retun<-paste0(as.character(retun),b)
return(retun)

}