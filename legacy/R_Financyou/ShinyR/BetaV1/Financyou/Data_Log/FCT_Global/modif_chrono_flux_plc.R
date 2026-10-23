##################################
#
# cree le 26/05/2020
# par SG
#
# ajouter les flux des plc avec credit/contrainte en automatique a tab_chrono
#
#####p#############################
#horiz=20
modif_chrono_flux_plc<- function(tab_chrono,debut_optim,revenu,credit,crd_imp,nom_plc) {
  # revenu<-recalcul_revenu
  # nom_plc<-nom_invest
  # crd_imp<-imp
  
  if (nom_plc=="RimmoPropre") {
    # mise a zero du loyer
    n<-which(tab_chrono$type=="life" & tab_chrono$sous.type=="hors_imp" & tab_chrono$sous.type_2=="loyer")
    tab_chrono[n,4:(horiz+3)]<-rep(debut_optim,horiz) # tab_chrono[n,]
    nom_plc<-"Votre logement"
    ## REVENU ##
    ## le credit est calcula partir de l'achat
    n<-which(tab_chrono$type=="plc" & tab_chrono$sous.type=="revenu" & tab_chrono$sous.type_2==nom_plc)
    tab_chrono[n,4:(horiz+3)]<-t(c(tab_chrono[n,4:(debut_optim-1+3)],rep(0,(horiz-debut_optim+1)))) # tab_chrono[n,]
    n<-which(tab_chrono$type=="plc" & tab_chrono$sous.type=="principal" & tab_chrono$sous.type_2==nom_plc)
    tab_chrono[n,4:(horiz+3)]<--t(c(rep(0,(debut_optim-1)),credit[[1]][1:(horiz-debut_optim+1)] ))
    n<-which(tab_chrono$type=="plc" & tab_chrono$sous.type=="interet" & tab_chrono$sous.type_2==nom_plc)
    tab_chrono[n,4:(horiz+3)]<--t(c(rep(0,(debut_optim-1)),credit[[2]][1:(horiz-debut_optim+1)] ))
    ## le crd imp est calcule depuis t0
    n<-which(tab_chrono$type=="plc" & tab_chrono$sous.type=="crd_imp" & tab_chrono$sous.type_2==nom_plc)
    tab_chrono[n,4:(horiz+3)]<-crd_imp
    
  } else {
    # revenu
    tab_chrono<-add_row(tab_chrono)
    n<-length(tab_chrono[,1])
    tab_chrono[n,1:3]<-c("plc","revenu",paste0("ajout_",nom_plc))
    tab_chrono[n,4:(horiz+3)]<-t(c(rep(0,(debut_optim-1)),rep(revenu,(horiz-debut_optim+1)) ))
      
    ## FLUX HORS IMPOTS ##
    tab_chrono<-add_row(tab_chrono)
    n<-length(tab_chrono[,1])
    tab_chrono[n,1:3]<-c("plc","principal",paste0("ajout_",nom_plc))
    tab_chrono[n,4:(horiz+3)]<--t(c(rep(0,(debut_optim-1)),credit[[1]][1:(horiz-debut_optim+1)] )) # tab_chrono[n,]
    
    tab_chrono<-add_row(tab_chrono)
    n<-length(tab_chrono[,1])
    tab_chrono[n,1:3]<-c("plc","interet",paste0("ajout_",nom_plc))    
    tab_chrono[n,4:(horiz+3)]<--t(c(rep(0,(debut_optim-1)),credit[[2]][1:(horiz-debut_optim+1)] ))
    
    tab_chrono<-add_row(tab_chrono)
    n<-length(tab_chrono[,1])
    tab_chrono[n,1:3]<-c("plc","crd_imp",paste0("ajout_",nom_plc))    
    tab_chrono[n,4:(horiz+3)]<-crd_imp # calcul depuis t=0
    
  }
  
 ### Recalcul Recap ###
 
  ###### calcul de l'impot paye en considerant les projets
  # calcul de l'impot
  a<-tab_chrono %>% filter( type=="life"|type=="plc"|type=="projets") %>% filter(sous.type=="revenu"|sous.type=="crd_imp"|sous.type=="part_imp" )
  QF<-apply(a %>% filter(sous.type=="revenu") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  nb_part<-tab_chrono %>% filter( type=="life", sous.type=="part_imp", sous.type_2=="avec projets")%>% select(-type,-sous.type,-sous.type_2)
  QF<-QF/nb_part
  a<--fct_flux_IR(QF)*nb_part+apply(a %>% filter(sous.type=="crd_imp") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  
  n<-which(tab_chrono$type=="impots" & tab_chrono$sous.type=="IR" & tab_chrono$sous.type_2=="final")
  tab_chrono[n,4:(horiz+3)]<-a # tab_chrono[n,]
  
  # Epargne libre projets deduits#
  a<-bind_rows(
    tab_chrono%>%filter(type=="life",sous.type=="hors_imp",sous.type_2=="depenses hors projets")
    ,tab_chrono%>%filter(type=="impots",sous.type=="IR_sup",sous.type_2==nom_plc)
    ,tab_chrono%>%filter(sous.type=="principal")
    ,tab_chrono%>%filter(sous.type=="interet")
    ,tab_chrono%>%filter(sous.type_2=="loyer")
  ) %>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  b<-tab_chrono%>%filter(sous.type=="revenu") %>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # projet hors_imp
  c<-tab_chrono %>% filter(type=="projets",sous.type=="hors_imp")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)

  n<-which(tab_chrono$type=="life" & tab_chrono$sous.type=="hors_imp" & tab_chrono$sous.type_2=="Epargne libre avec projets")
  tab_chrono[n,4:(horiz+3)]<--(b+a+c) # tab_chrono[n,]
  
  ###### cacul du credit sup max ######
  taux_endet_max<-0.33
  taux_compt_div<-0.75
  # revenu
  a<-tab_chrono %>% filter(sous.type=="revenu",type!="plc")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # loyer recu
  b<-tab_chrono %>% filter(sous.type=="revenu",type=="plc")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  b<- taux_compt_div * b
  # pension recue 
  # c<-
  # charges
  # loyer verse
  d<- tab_chrono %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # credit en cours
  e<- tab_chrono %>% filter(sous.type=="principal" | sous.type=="interet")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # pension versee
  # f<-
  
  n<-which(tab_chrono$type=="life" & tab_chrono$sous.type=="credit sup" & tab_chrono$sous.type_2==0)
  tab_chrono[n,4:(horiz+3)]<-taux_endet_max *(a+b) + (d+e) # tab_chrono[n,]
  
  #########################################

  return(tab_chrono)
}
