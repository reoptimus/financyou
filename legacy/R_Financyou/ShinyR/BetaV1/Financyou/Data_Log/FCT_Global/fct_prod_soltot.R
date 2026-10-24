##################################
#
# cree le 23/10/2020
# par SG
#
# production de Soltot: matrice des répartition optimum
# fonction des contraintes, duree inves, debut invest
#
##################################
#horiz=20
fct_prod_soltot<- function(tabl_pourc_cont0,Aversion,taux_marg_retenu,list_placements_compl,horiz) {
  # tabl_pourc_cont0<-tabl_pourc_conti
  # Aversion<-5
  # list_placements_compl<-list_plac_optim
  #   unique(List_alpha_approx$Apetence)
  # List_alpha_approx & Tab_alpha_approx sont ds global
  ## calcul approche de soltot
  
  # simplification des resultats
  tabl_pourc_cont0[which(tabl_pourc_cont0<1e-3,arr.ind = TRUE)]<-0
  
  List_alpha_app_compl<- List_alpha_approx %>% filter(Apetence==Aversion) %>%
    filter(GSE==paste0("Tr_imp_",as.character(taux_marg_retenu)))
  Tab_alpha_app<-Tab_alpha_approx
  soltot<-array(0,dim=c(length(list_placements_compl),horiz,horiz))
  
  for (i in 1:dim(tabl_pourc_cont0)[2]) { # i=3
    List_alpha_app<-List_alpha_app_compl
      
    cont_immo<- max(tabl_pourc_cont0[which(list_placements_compl=="RimmoPropre"),i],0)
    cont_crd_immo<- max(-tabl_pourc_cont0[which(list_placements_compl=="crd_RimmoPropre"),i],0)
    cont_pinel<- max(tabl_pourc_cont0[which(list_placements_compl=="RimmoPinel"),i],0)
    if (cont_pinel!=0) {
      cont_crd_pinel<- max(tabl_pourc_cont0[which(list_placements_compl=="crd_RimmoPinel"),i],0)
    } else { # on assimile l'invest locatif en pinel
      cont_pinel<- max(tabl_pourc_cont0[which(list_placements_compl=="RimmoLoc"),i],0)
      cont_crd_pinel<- max(tabl_pourc_cont0[which(list_placements_compl=="crd_RimmoLoc"),i],0)
    }
    
    # elimination des lignes inutiles
    if (cont_crd_immo==0) { # pas de contrainte sur immo
      List_alpha_app<-List_alpha_app[List_alpha_app$crd_ImmoPropre==0,]
    } else {
      List_alpha_app<-List_alpha_app[List_alpha_app$crd_ImmoPropre!=0,]
    }
    if (cont_crd_pinel==0) { # pas de contrainte sur immo
      List_alpha_app<-List_alpha_app[List_alpha_app$crd_Pinel==0,]
    } else {
      List_alpha_app<-List_alpha_app[List_alpha_app$crd_Pinel!=0,]
    }
    dim(List_alpha_app)
    
    # calcul de la distance dans l'espace des contraintes: ici de dim 4 
    a <- as.data.frame(List_alpha_app[,5:8])-t(array(rep(c(cont_immo,cont_crd_immo,cont_pinel,cont_crd_pinel),dim(List_alpha_app)[1]),dim=c(4,dim(List_alpha_app)[1])))
    a <- ( as.data.frame(apply(a^2,1,sum)) )^0.5
    # selection des 2 plus proches voisins
    pt1<-List_alpha_app[which.min(a[,1]),]$num
    dist1<-min(a[,1])
    a[which.min(a[,1]),1]<-100
    pt2<-List_alpha_app[which.min(a[,1]),]$num
    dist2<-min(a[,1])
    # ponderation du resultat en fonction de la distance aux 2 plus proches voisins
    soltot[,,i]<-((1-dist1/(dist1+dist2))*Tab_alpha_approx[,,pt1]+(1-dist2/(dist1+dist2))*Tab_alpha_approx[,,pt2])
    # dim(soltot)
    
    ##### remises des contraintes exactes et normalisation ####
    vector<-tabl_pourc_cont0[,i]
    a<-which(vector!=0, arr.ind =TRUE)
    b<-vector[which(vector!=0, arr.ind =TRUE)]
    soltoti<-soltot[,,i]
    soltoti[a,]<-0
    for (j in 1:length(vector)){
      soltot[j,,i]<-soltot[j,,i]*( (1-sum(vector))/ apply(soltoti,2,sum) )
    }
    soltot[a,,i]<-array(rep(b,horiz),dim=c(length(a),horiz))
    ###########################
    # apply(soltot[,,i],2,sum)
  }
  # plot soltot
  # D<-1:20
  # plot(soltot[1,D,10],ylim=c(0,1))
  # for (i in 10:11){
  #   lines(soltot[i,D,10],type="l",col=i)
  # }
  # for (i in 12:13){
  #   lines(soltot[i,D,10],type="o",col=i)
  # }
  # soltot[c(10,12),1,10]
  # dim(soltot)
  
  return(soltot)
  
}