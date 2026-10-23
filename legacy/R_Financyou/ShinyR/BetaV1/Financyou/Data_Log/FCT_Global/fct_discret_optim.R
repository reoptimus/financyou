########################
# cree le 02/10/2020
# par SG
#
# Fonction de discretisation des credit dans l'optimum marko
#
#######################

discret_optim<- function(tabl_plac,Mat_result_final,tabl_eur_cont,tab_chrono,proj="Y") {
  
  # proj<-"Y" # ou "N" projet
  mini_immo<-200000 # montant mini pour de l immo, a verifier!
  montant<-mini_immo
  horiz<-dim(Mat_result_final)[2]
  list_nom<-list_placements_compl[[2]]
  
  # definition des actifs proposés, non deja contraints, avec un engagement suffisant (>1000) et non-liquide avec credit
  a<-which(apply(tabl_eur_cont[,2:(horiz+1)],1,sum)==0) # sans contraintes
  b<-which(abs(apply(tabl_eur_cont[,2:(horiz+1)],1,sum)+apply(Mat_result_final[,1:(horiz)],1,sum))>1000)
  list_Notliquide<-as.character(table_invest$placements[which(table_invest$Liquide==0)]) #pas liquide
  list_Notliquide<-c(list_Notliquide,paste0("crd_",list_Notliquide))
  c<-sapply(list_placements_compl[[2]],function(x) which(x==list_Notliquide))
  c<-which(as.data.frame(t(c))>=1) # non liquide
  d<- grep("crd_",list_nom)
  
  new_crd<-sort( intersect(intersect(intersect(a,b),c),d) ) #proposition de nouveau crdit
  
  if ( length(new_crd)!=0 ) { # des actifs non liquide a discretiser
    if (length(new_crd)>1) { new_crd<-new_crd[1] }
   
    nom_apport<- substr(list_nom[new_crd],5,nchar(as.character(list_nom[new_crd])) )
    num_apport<- which(list_nom==nom_apport)
    recalcul_revenu<-fct_recalcul_revenu(nom_apport,montant,tab_chrono)
    # tau<-0
    # nom_invest<-""
    revenu<-0
    ind<-0
    
    while ( abs(revenu-recalcul_revenu) > (0.05*revenu) ) { #boucle pour converger sur les loyers a appliquer dans la simu
    # fonction du recalcul du revenu en fonction du type nom_apport
    revenu<-recalcul_revenu
    ind<-ind+1
    annuite_floue<-Mat_result_final[new_crd,] #conseil d'invest remboursement credit en eur cumul hors rendement du placement (ici loyers)
    apport_floue<- Mat_result_final[num_apport,]
    
      if (proj=="Y") {
        # verification des limite de remboursement (33%) avec / sans projets
        credit_sup<- tab_chrono %>% filter(type=="life", sous.type=="credit sup",sous.type_2=="avec projets") %>% select(-type,-sous.type,-sous.type_2)
        apport_sup<- tab_chrono %>% filter(type=="life", sous.type=="hors_imp",sous.type_2=="Epargne libre avec projets") %>% select(-type,-sous.type,-sous.type_2)
      } else {
        # verification des limite de remboursement (33%) avec / sans projets
        credit_sup<- tab_chrono %>% filter(type=="life", sous.type=="credit sup",sous.type_2=="hors projets") %>% select(-type,-sous.type,-sous.type_2)
        apport_sup<- tab_chrono %>% filter(type=="life", sous.type=="hors_imp",sous.type_2=="Epargne libre hors projets") %>% select(-type,-sous.type,-sous.type_2)
      }

    credit_sup[which(credit_sup<0)]<-0
    credit_sup[which(credit_sup>0)]<-credit_sup[which(credit_sup>0)]+revenu
    credit_sup<-cumsum(as.list(credit_sup))
    apport_sup<--apport_sup
    apport_sup[which(apport_sup<0)]<-0
    apport_sup<-cumsum(as.list(apport_sup))
    
    # plot(1:length(apport_sup),apport_sup,ylim=c(0,1000000))
    # lines(1:length(apport_sup),(apport_sup+credit_sup),col="red")
    # lines(apport_floue,type="o",col="green")
    # lines((apport_floue+annuite_floue),col="blue")
    
    #### formule pour discretiser le credit ####
    
    # prolongation de apport_sup+credit_sup
    apport_floue<-pmin(apport_floue,apport_sup)
    pente_end_floue<-annuite_floue[length(annuite_floue)]-annuite_floue[length(annuite_floue)-1]
    pente_end_sup<-credit_sup[length(credit_sup)]-credit_sup[length(credit_sup)-1]
    
    # on allonge la serie au dela de horiz
    apport_floue<-c(apport_floue,apport_floue[horiz]+seq(1,horiz,1)*(apport_floue[horiz]-apport_floue[horiz-1]))
    annuite_floue<-c(annuite_floue,annuite_floue[horiz]+seq(1,horiz,1)*(annuite_floue[horiz]-annuite_floue[horiz-1]))

    # optimisation avec [[1]]<-ratio , [[2]]<-annnuite , [[3]],apport
    a<-sapply(1:(horiz-1),function(x) optim_tang(x,apport_floue,annuite_floue,horiz))
    # debut_optim<-which(a[1,]==max(a[1,]))
    # plot(1:(horiz-1),a[1,])
    
    # calcul des caracteristiques de l'emprunt
    nom_invest<-nom_apport
    tau<-table_invest$Spread_emprunt[which(table_invest$placements== nom_invest)]
    n<-table_invest$annee_empr[which(table_invest$placements== nom_invest)]
    emprunt<-as.numeric(a[2,])*(1-(1+tau)^-n)/tau
    montant<-emprunt+as.numeric(a[3,])
    
    apport_mini<-0.1*montant # 10% du montant du bien hors frais
    apport_possible<-(apport_mini[1:horiz]<apport_sup[1:horiz])
    # on prolonge lineairement l'apport mini au dela d'horiz
    apport_mini<-c(apport_mini,apport_mini[horiz-1]+seq(1,horiz+1,1)*(apport_mini[horiz-1]-apport_mini[horiz-2]))
    
    # recalcul avec l'apport mini et conservation de la meilleur couverture
    b<-sapply(1:(horiz-1),function(x) optim_tang(x,apport_mini,annuite_floue,horiz))
    # plot(1:(horiz-1),a[1,])
    # lines(1:(horiz-1),b[1,],type="l",col="red")
    
    # elimiination des solutions qui ne peuvent pas etre financees
    a[1,][ which(apport_possible==FALSE) ]<-0
    b[1,][ which(apport_possible==FALSE) ]<-0
    # meilleur solution retenue
    if ( max(as.data.frame(b[1,])) > max(as.data.frame(a[1,])) ) {
      debut_optim<-which(b[1,]==max(as.data.frame(b[1,])) ) # meilleur ratio de couverture de l'optimum selon Marko
      annuite<-b[2,debut_optim]
      apport<-b[3,debut_optim]
      } else {
      debut_optim<-which(a[1,]==max(as.data.frame(a[1,])))
      annuite<-a[2,debut_optim]
      apport<-a[3,debut_optim]
      }
    
    # calcul des caracteristiques de l'emprunt
    emprunt<-as.numeric(annuite)*(1-(1+tau)^-n)/tau
    montant<-emprunt+as.numeric(apport)
    
    recalcul_revenu<-fct_recalcul_revenu(nom_apport,montant,tab_chrono)
  }

    # verification des limite
    if (  montant>=mini_immo ) { # montant mini pour un invest immo
      # creer les lignes dans tab_chrono: nom_invest="RimmoPinel"
      credit<- Flux_crd(horiz,annuite[[1]],tau,n) # principale,interet
      imp<- fct_flux_crd_imp(nom_invest,montant,0,horiz,1,debut_optim)
      } else {
      # pas d'investissement dans ce support doit etre bloque a zero
      credit<- Flux_crd(horiz,0,tau,n) # principale,interet tau<-0.01 n<-20
      imp<-fct_flux_crd_imp(nom_invest,0,0,horiz) # nom_invest<-"Votre logement"
      recalcul_revenu<-0
      montant<-0
      annuite<-0
      }
    
    tab_chrono_new<- modif_chrono_flux_plc(tab_chrono,debut_optim,recalcul_revenu,credit,imp,nom_invest)
    # tab_chrono_new<-tab_chrono
    tabl_plac_new<- modif_tabl_plac(tabl_plac,montant,annuite,tau,debut_optim,n,recalcul_revenu,nom_invest)

    return (list(tab_chrono_new,new_crd,tabl_plac_new))
  } else { # pas d actifs non liquide selectionne dans l'optimum
    new_crd<-0
    return(list(tab_chrono,new_crd,tabl_plac))
  }
 
}
