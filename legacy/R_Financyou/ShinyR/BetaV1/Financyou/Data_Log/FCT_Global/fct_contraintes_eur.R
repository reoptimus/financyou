#########################☻
#
# Fonction pour definir les contraintes en eur a partir des placements et projets
#
# cree le 09/06/2020
# par Sebastien gallet
# financyou.com

contraintes<-function(tabl_placi,list_placements_compli,tab_chrono_cumuli,projeti="Y") {
  
  # tabl_placi<-tabl_plac
  # list_placements_compli<- list_placements_compl
  # tab_chrono_cumuli<-tab_chrono_cumul

  
  tabl_eur_cont<-data.frame(list_placements_compli,t(rep(0,horiz)))
  eng_t0<-data.frame(list_placements_compli,t(rep(0,horiz)))
  
  # verif tab_chrono
  # a<-apply(sum_cuml_tab[,2:21],2,sum)
  # b<-tab_chrono_cumuli%>% filter(sous.type=="revenu")%>%select(-type,-sous.type,-sous.type_2)%>%summarise_all(sum)
  # a+b
  
  #### mise en forme pour les tranches multi support (ex: ass vie eur/uc) ####
  i=1
  for (i in 1:length(tabl_placi$nom_plc)) {
    apport<-rep(0,horiz)
    Part1<-tabl_placi$Part_Tr_GSE1[i]
    Part2<-tabl_placi$Part_Tr_GSE2[i]
    ligne1<-which(list_placements_compli==tabl_placi$nom_Tr_GSE1[i])
    if (Part2!="0") { ligne2<-which(list_placements_compli==tabl_placi$nom_Tr_GSE2[i]) }
    
    if(tabl_placi$Annuite[i]!=0 ) { 
      # si on a deja un credit
      if (projeti=="Y") {
        lign_eur_cont<- tab_chrono_cumuli %>% 
          filter(sous.type=="principal",sous.type_2==tabl_placi$nom_plc[i]) %>%
          select(-type,-sous.type,-sous.type_2)%>%
          summarise_all(sum)
      } else {
        lign_eur_cont<- tab_chrono_cumuli %>% 
          filter(type!="projets",sous.type=="principal",sous.type_2==tabl_placi$nom_plc[i]) %>%
          select(-type,-sous.type,-sous.type_2)%>%
          summarise_all(sum)
      }
  
      lign_crd<-ligne1
      if (list_placements_compli[ligne1]=="RimmoPropre") { # pour l eng de l habitation
        lign_crd<-which(list_placements_compli=="crd_RimmoPropre")
      } else {
        lign_crd<-tab2_plc$Equiv__Crd[which(tab2_plc$Equiv_GSE1==list_placements_compli[ligne1])]
        lign_crd<-which(list_placements_compli==lign_crd)
        if (lign_eur_cont[1]==0) { # c'est un proj
          apport<-rep(0,horiz)
          if (is.integer0(which(lign_eur_cont!=0))==FALSE) {
            apport[which(lign_eur_cont!=0)]<-lign_eur_cont[which(lign_eur_cont!=0)[1]]
          }
          apport<-t(as.matrix(apport))
        }
      }
      tabl_eur_cont[lign_crd,2:(horiz+1)]<-as.numeric(Part1)*(lign_eur_cont-apport)
      tabl_eur_cont[ligne1,2:(horiz+1)]<-tabl_eur_cont[ligne1,2:(horiz+1)]+apport
      eng_t0[ligne1,2:(horiz+1)]<- as.numeric(Part1)*rep(tabl_placi$V0_net[i],horiz)
      
      # si il y a deux table GSE++ pour cet actif
      if (Part2!="0") {
        tabl_eur_cont[ligne2,2:(horiz+1)]<-as.numeric(Part2)*lign_eur_cont
        eng_t0[ligne2,2:(horiz+1)]<- as.numeric(Part2)*rep(tabl_placi$V0_net[i],horiz)
      } 
    } else { # si pas d annuites
      if (tabl_placi$sous_type[i]=="ajout") { # on bloque le placement a zero
        tabl_eur_cont[ligne1,2:(horiz+1)]<--rep(1,horiz)
        lign_crd<-which(tabl_eur_cont$list_placements_compli==paste0("crd_",tabl_placi$nom_Tr_GSE1[i]))
        tabl_eur_cont[lign_crd,2:(horiz+1)]<--rep(1,horiz)
      } else { # placement non bloque
        tabl_eur_cont[ligne1,2:(horiz+1)]<--rep(tabl_placi$Valeur_t0[i],horiz)
        
      }
    }
  }
  
  # retrait des sommes deja engagee a t0 et des annuite futur
  tabl_eur_cont[,2:(horiz+1)]<-tabl_eur_cont[,2:(horiz+1)]-eng_t0[,2:(horiz+1)]
  
  return(list(tabl_eur_cont,eng_t0))
} # fin de la fonction contraintes
