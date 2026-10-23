#######################
#
# Lancement MOCA : Calcul global a partir du GSE
# 
#
# modifie le 26/05/2020
# par Sebastien Gallet
#########################

MOCA <- function (tabl_plac,tab_chrono,horiz,Num_Av,List_Av,numerotation_GSE,projet_incl) {

  # projet_incl="N"
  # List_Av[Num_Av]
  
  ##### chargement du GSE++ correspondant au taux marginal IR ###########
  # a modifier, rearanger les GSE pour qu'ils tiennent compte de l'evolution du taux marginal d'IR
  taux_marg_retenu<-as.numeric(tab_chrono %>% filter( type=="impots") %>% filter(sous.type=="taux_marg_IR")%>% filter(sous.type_2=="final")%>% select(-type,-sous.type,-sous.type_2)
  )[10]
  load(paste0(reptravail,chemin,"Data_Log/GSE++/","GSE++_",numerotation_GSE,"_",as.character(taux_marg_retenu),".Rda"))
  # list_placements : listes des placements du GSE++
  #####
  
  # liste des placements possibles
  list_plac_optim<-list_placements_compl[[2]]
  num_plac_optim<-list_placements_compl[[1]]
  # list_placements_compl [[1]]-> num slide GSE [[2]] noms des slides
  
  list_plac_user<-unique(c(tabl_plac$nom_Tr_GSE2,tabl_plac$nom_Tr_GSE1))
  list_plac_user<-list_plac_user[-which(list_plac_user=="NULL")]

  ###### efface les tranche du GSE++ inutiles ######
  l<-c()
  for (i in 1:length(list_plac_optim) ) {
    # tranche du GSE qui correspond a la list placement
    l<-c(l,which(list_placements==list_plac_optim[i]))
  }
  GSEpp_cuml<-GSE_plac_taxes_cuml[,,,l]
  rm(GSE_plac_taxes_cuml)
  gc()
  ###### dim(GSEpp_cuml)
  

  ###### cumul de tab_chrono #####
  tab_chrono_cumul<-tab_chrono
  # dim(tab_chrono)
  for (i in 5:(horiz+3)) {
    tab_chrono_cumul[,i]<-tab_chrono_cumul[,i]+tab_chrono_cumul[,(i-1)]
  }
    
    ##### calcul des contraintes user et sum_cuml_tab ######
      contraint<-contraintes(tabl_plac,list_plac_optim,tab_chrono_cumul,projet_incl) # Y avec projets, N sans
      sum_cuml_tab<-CF_avec_proj(tab_chrono,horiz,projet_incl)
    
    ##### construction de tabl_eur_cont: les contraintes en eur par actif #####
      tabl_eur_cont<-contraint[[1]]
      eng_t0<-contraint[[2]]
      
      # flux cumul total de l epargne
      sum_cuml<- sum_cuml_tab %>% filter(  type!="Depenses courantes" &
                                             type!="impots" &
                                             type!="Interets du credit habitation" &
                                             type!="Interets des credits placements" &
                                           type!="Loyer" &
                                           type!="Depenses projets hors impots"
    )%>% select(-type) %>% summarise_all(sum)
      # plot(1:20,-sum_cuml)
    sum_cuml<-sum_cuml-rep(sum(tabl_plac$V0_net),horiz)
    
    ##### contraintes en % pour l'optimisation #####
    tabl_pourc_conti<- as.data.frame( tabl_eur_cont[,2:(horiz+1)] , strings2factor=FALSE)
    for (i in 1:dim(tabl_pourc_conti)[1]) {
      tabl_pourc_conti[i,]<-tabl_pourc_conti[i,]/sum_cuml
    }
    # Verif: apply(tabl_pourc_cont,2,sum) # % contraint selon les annees
    
    ##### calcul de soltot approx ###############
    # List_alpha_approx & Tab_alpha_approx sont ds global
    soltot<-fct_prod_soltot(tabl_pourc_conti,List_Av[Num_Av],taux_marg_retenu,list_plac_optim,horiz)
    
    ##### stripping du flux sans engagement ####
    mat_strip<-stripping(pas_E,-sum_cuml)
    
    ##### ASSEMBLAGE SOLUTION ####################
    Mat_result <- Assembl_invest(soltot,mat_strip,GSEpp_cuml,-sum_cuml)
  
    return(list(Mat_result,tabl_eur_cont))
  
} # fin de la function


