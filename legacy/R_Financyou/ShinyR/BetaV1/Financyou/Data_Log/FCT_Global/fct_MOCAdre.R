########################
#
# MOCAdre : fct cadre du moteur de calcul MOCA
#
# le 06/11/2020
# par SG
########################

MOCAdre <- function (hist_,tab_chrono,horiz,Num_Av,List_Av,numerotation_GSE) {
  
  # List_Av<- c(0.5, 5,50)
  # Num_Av<-2
  proj_list<-c("Y","N")
  nb_crd<-1
  Rdt_liquide<-list("","")
  List_def<-list("","")
  Mat_result_graph<-list("","")
  
  ####### placements pris par le user: tabl_plac #####
  tabl_plac<-as.data.frame(hist_$plc[[1]])
  # on retire les placements vide : immo propre lorsque qu on est locataire
  tabl_plac<-tabl_plac[which(tabl_plac$Valeur_t0!=0),]
  # placement projet immo sans la colonne ligne_proj
  tabl_plac$Part_Tr_GSE1<-as.numeric(tabl_plac$Part_Tr_GSE1)
  tabl_plac$Part_Tr_GSE2<-as.numeric(tabl_plac$Part_Tr_GSE2)
  if ( length(hist_$plc_immo[[1]])!=0 ) {
    tabl_plac_proj<-as.data.frame(hist_$plc_immo[[1]]) %>% select(-ligne_proj)
    tabl_plac_proj$V0_net<-0
    tabl_plac<-bind_rows(tabl_plac,tabl_plac_proj)
  }
  ##########################################
   
  j=1
  i=1 # i=3
for (j in 1:2) { # boucle avec/sans projets
  while (nb_crd!=0) { # boucle tant qu'il y a des actif_crd non liquide
    #lancement de MOCA
    Mat_result<-MOCA(tabl_plac,tab_chrono,horiz,Num_Av,List_Av,numerotation_GSE,proj_list[j])
    Mat_result_final <-Mat_result[[1]][[1]]
    tabl_eur_cont<-Mat_result[[2]]
  
    # optimisation discrete de la solution Marko continue
    ### mise a jour de tab_chrono ####
    tab_chrono_new<-discret_optim(tabl_plac,Mat_result_final,tabl_eur_cont,tab_chrono,proj_list[j])
    nb_crd<-tab_chrono_new[[2]]
    tab_chrono<-tab_chrono_new[[1]]
    ### mise a jour de table placement tabl_plac ####
    tabl_plac<-tab_chrono_new[[3]]
  }
  # enregistrement des donnes a presenter a la fin de l'optim
  Rdt_liquide[[j]]<-Mat_result[[1]][[2]]
  List_def[[j]]<-as.data.frame(list_placements_compl[[2]][which(apply(Mat_result_final,1,sum)!=0)])
  Mat_result_graph[[j]]<-Mat_result_final[which(apply(Mat_result_final,1,sum)!=0),]
}
  
  return(list(Mat_result_graph,Rdt_liquide,List_def,list_placements_compl)) # ATTENTION 3 matrice en list()
  
}
