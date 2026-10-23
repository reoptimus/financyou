##################################
#
# cree le 05/08/2020
# par SG
#
#
# flux life: revenu:  revenu_sal
#            Part imposable : structure foyer
#            Flux hors impots: depense, loyer, remboursement principale, interet credit
# recuperer plot_revenu.R et modifier
# 1- rassembler les donnes hist()
# 2 - creer des chronologies par type (life/plc/projets) / sous-type (revenu/hors_imp/part/crd_imp) dans un tableau
##################################
#horiz=20
fct_chrono_flux<- function(horiz,hist_) {
  tab_chrono<-data.frame("type"=character(1),
                         "sous-type"=character(1),
                         "sous-type_2"=character(1),
                         stringsAsFactors = FALSE)
  a<-array(rep(0),dim=c(1,(horiz)))
  a<-as.data.frame(a)
  tab_chrono<-cbind(tab_chrono,a)
  #str(tab_chrono)
  
  ##### ligne a ligne des flux ########
  ########### REVENU et loyer ######
  nb_sal<-as.numeric(as.data.frame(hist_$revenu[[1]])$nb_sal)
  Net_imposable<-as.numeric(as.data.frame(hist_$revenu[[1]])$Net_imposable)
  sal2<-as.numeric(as.data.frame(hist_$revenu[[1]])$sal2)
  if (nb_sal==1) {sal2=0}
  # sal1
  tab_chrono[1,1]<-"life"
  tab_chrono[1,2]<-"revenu"
  tab_chrono[1,3]<-"sal1"
  sal1<-Net_imposable
  evol_sal<-as.data.frame(hist_$revenu[[1]])$evol_sal
  box_evol_sal<-as.data.frame(hist_$revenu[[1]])$box_evol_sal
  tab_chrono[1,4:(horiz+3)]<- rep(Net_imposable,horiz)*(1+evol_sal)^(seq(horiz)-1)
  # ajout retraite sur sal1
  Res_retraite1<-as.numeric(as.data.frame(hist_$revenu[[1]])$res_retraite1)
  if (Res_retraite1<horiz) {
    Metier1<-as.character(as.data.frame(hist_$revenu[[1]])$metier1)
    taux_rempla<-tab_retraite[which(tab_retraite[,1]==Metier1),2]
    pente_rempla<-tab_retraite[which(tab_retraite[,1]==Metier1),3]
    taux_rempla<-taux_rempla*(1+pente_rempla*Res_retraite1)
    coef_rempla<-tab_coef_retraite[which(tab_coef_retraite[,1]==evol_sal),2]
    taux_rempla<- taux_rempla * coef_rempla #impact des 25 dernieres annees
    tab_chrono[1,(4+Res_retraite1):(horiz+3)]<-rep(tab_chrono[1,(4+Res_retraite1)]*taux_rempla,(horiz-Res_retraite1) )
  }
  
  # sal 2
  tab_chrono[2,1]<-"life"
  tab_chrono[2,2]<-"revenu"
  tab_chrono[2,3]<-"sal2"
  
  evol_sal2<-as.data.frame(hist_$revenu[[1]])$evol_sal2
  if (nb_sal==2){
    tab_chrono[2,4:(horiz+3)]<- rep(sal2,horiz)*(1+evol_sal2)^(seq(horiz)-1)
    # ajout retraite
    Res_retraite2<-as.numeric(as.data.frame(hist_$revenu[[1]])$res_retraite2)
    if (Res_retraite2<horiz) {
      Metier2<-as.character(as.data.frame(hist_$revenu[[1]])$metier2)
      taux_rempla<-tab_retraite[which(tab_retraite[,1]==Metier2),2]
      pente_rempla<-tab_retraite[which(tab_retraite[,1]==Metier2),3]
      taux_rempla<-taux_rempla*(1+pente_rempla*Res_retraite2)
      coef_rempla<-tab_coef_retraite[which(tab_coef_retraite[,1]==evol_sal2),2]
      taux_rempla<- taux_rempla * coef_rempla #impact des 25 dernieres annees
      tab_chrono[2,(4+Res_retraite2):(horiz+3)]<-rep(tab_chrono[2,(4+Res_retraite2)]*taux_rempla,(horiz-Res_retraite2) )
    }
  } else { # pas de deuxieme adulte
    tab_chrono[2,4:(horiz+3)]<-as.numeric(rep(0,horiz))
  }
  
  # pension avec prise en compte de l age
  tab_chrono[3,1]<-"life"
  tab_chrono[3,2]<-"revenu"
  tab_chrono[3,3]<-"pension"
  pension<-as.data.frame(hist_$fisc[[1]])$pension
  montant<-as.numeric(as.data.frame(hist_$fisc[[1]])$mont_pens)
  # c("recue","pas de pension","versée")
  # limite de pension fixee Ã 18 ans pourle plus agé
  limite_age<-18
  if ( lapply(hist_$fisc[[1]]$age_enf[[1]],sum) !=0 ) {
    list_age<-hist_$fisc[[1]]$age_enf$data[[1]]
    duree_part_enf<- limite_age - list_age[which( list_age!=0 ),]
    enf_max<-min(duree_part_enf) } else { # pas d enfant a charge
      enf_max<-10 # 
    }
  if (pension=="recue") {montant<- montant*12 }
  if (pension=="versée") { montant<- -montant*12}
  if (pension=="pas de pension") { montant<-0 }
  tab_chrono[3,4:(horiz+3)]<- Exp_fin(horiz-1,Sys.Date(),montant,montant,enf_max,0,0)
  
  # loyer habitation #
  tab_chrono[4,1]<-"life"
  tab_chrono[4,2]<-"hors_imp"
  tab_chrono[4,3]<-"loyer"
  Loyer<-as.data.frame(hist_$fiche[[1]])$Loyer
  if (Loyer!=0) {
    tab_chrono[4,4:(horiz+3)]<--rep(Loyer,horiz)
  } else {tab_chrono[4,4:(horiz+3)]<-rep(0,horiz)}
  
  lim<-dim(tab_chrono)[1]
  
  
  #### PART IMPOSABLE  hors projets #####
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"part_imp"
  tab_chrono[lim+1,3]<-"hors projets"
  nb_part<-as.data.frame(hist_$revenu[[1]],stringsAsFactors = FALSE)$nb_sal
  chrono_projet_part_imp<-rep(nb_part,horiz)
  # limite de declaration fixee Ã 20 ans
  limite_age<-20
  if ( lapply(hist_$fisc[[1]]$age_enf[[1]],sum) !=0 ) {
    list_age<-hist_$fisc[[1]]$age_enf$data[[1]]
    duree_part_enf<- limite_age - list_age[which( list_age!=0 ),]
    for (i in 1:dim(duree_part_enf)[1] ) {
      if (i<=2) {enf<-0.5} else {enf<-1}
      chrono_projet_part_imp<- chrono_projet_part_imp+Exp_fin(horiz-1,Sys.Date(),enf,enf,duree_part_enf[i,],0,0)
    }
  }
  tab_chrono[lim+1,4:(horiz+3)]<-chrono_projet_part_imp
  
  lim<-dim(tab_chrono)[1]
  
  #########  PROJETS  #######
  # flux projets : deja fait, rappatrier le code ici
  projet<-as.data.frame(hist_[,"projets"][[1]],stringsAsFactors = FALSE)
  # revenu
  for (i in 1:length(projet[,1]) ) {
    tab_chrono[lim+i,1]<-"projets"
    tab_chrono[lim+i,2]<-"revenu"
    tab_chrono[lim+i,3]<-projet[i,"nom_projet"]
    tab_chrono[lim+i,4:(horiz+3)]<-c(as.data.frame(projet$chrono_projet_revenu[[i]],stringsAsFactors = FALSE),rep(0,100))[1:horiz]
  }
  lim<-dim(tab_chrono)[1]
  # epargne hors impot
  for (i in 1:length(projet[,1]) ) {
    tab_chrono[lim+i,1]<-"projets"
    tab_chrono[lim+i,2]<-"hors_imp"
    tab_chrono[lim+i,3]<-projet[i,"nom_projet"]
    tab_chrono[lim+i,4:(horiz+3)]<-c(as.data.frame(projet$chrono_projet_epar[[i]],stringsAsFactors = FALSE),rep(0,100))[1:horiz]
  }
  lim<-dim(tab_chrono)[1]
  # part impot
  for (i in 1:length(projet[,1]) ) {
    tab_chrono[lim+i,1]<-"projets"
    tab_chrono[lim+i,2]<-"part_imp"
    tab_chrono[lim+i,3]<-projet[i,"nom_projet"]
    tab_chrono[lim+i,4:(horiz+3)]<-c(as.data.frame(projet$chrono_projet_part_imp[[i]],stringsAsFactors = FALSE),rep(0,100))[1:horiz]
  }
  lim<-dim(tab_chrono)[1]
  # credit impot
  for (i in 1:length(projet[,1]) ) {
    tab_chrono[lim+i,1]<-"projets"
    tab_chrono[lim+i,2]<-"crd_imp"
    tab_chrono[lim+i,3]<-projet[i,"nom_projet"]
    tab_chrono[lim+i,4:(horiz+3)]<-c(as.data.frame(projet$chrono_projet_crd_imp[[i]],stringsAsFactors = FALSE),rep(0,100))[1:horiz]
  }
  lim<-dim(tab_chrono)[1]
  
  # Principal immo
  for (i in 1:length(projet[,1]) ) {
    tab_chrono[lim+i,1]<-"projets"
    tab_chrono[lim+i,2]<-"principal"
    tab_chrono[lim+i,3]<-projet[i,"nom_projet"]
    tab_chrono[lim+i,4:(horiz+3)]<-c(as.data.frame(projet$chrono_projet_principal[[i]],stringsAsFactors = FALSE),rep(0,100))[1:horiz]
  }
  lim<-dim(tab_chrono)[1]
  # Part_conso
  for (i in 1:length(projet[,1]) ) {
    tab_chrono[lim+i,1]<-"projets"
    tab_chrono[lim+i,2]<-"part_conso"
    tab_chrono[lim+i,3]<-projet[i,"nom_projet"]
    tab_chrono[lim+i,4:(horiz+3)]<-c(as.data.frame(projet$chrono_projet_part_conso[[i]],stringsAsFactors = FALSE),rep(0,100))[1:horiz]
  }
  lim<-dim(tab_chrono)[1]
  
  #########  PLC ########
  # flux plc : revenu:  loyers, dividendes , frais, interet credit
  #            Flux hors impots: frais, remboursement principale
  tabl_plac<-as.data.frame(hist_$plc[[1]])
  
  #fonction de transf d'un credit en flux principal,interet
  nb_plc<-length(tabl_plac[,1])
  i=1
  for (i in 1:nb_plc) {
    ## REVENU ##
    tab_chrono[lim+i,1]<-"plc"
    tab_chrono[lim+i,2]<-"revenu"
    tab_chrono[lim+i,3]<-tabl_plac[i,"nom_plc"]
    tab_chrono[lim+i,4:(horiz+3)]<-tabl_plac[i,"Revenu"]
    ## FLUX HORS IMPOTS ##
    a<-Flux_crd(horiz,tabl_plac$Annuite[i],tabl_plac$Taux[i],tabl_plac$An_rest[i])
    tab_chrono[lim+i+nb_plc,1]<-"plc"
    tab_chrono[lim+i+nb_plc,2]<-"principal"
    tab_chrono[lim+i+nb_plc,3]<-tabl_plac[i,"nom_plc"]
    tab_chrono[lim+i+nb_plc,4:(horiz+3)]<--a[[1]]
    
    tab_chrono[lim+i+2*nb_plc,1]<-"plc"
    tab_chrono[lim+i+2*nb_plc,2]<-"interet"
    tab_chrono[lim+i+2*nb_plc,3]<-tabl_plac[i,"nom_plc"]
    tab_chrono[lim+i+2*nb_plc,4:(horiz+3)]<--a[[2]]
    ## CREDIT IMPOT EN COURS ##
    # test si "sous-type" == niche fiscale, si oui fct_flux_crd_imp (type_niche,montant_aujourd,age_de l'invest)
    tab_chrono[lim+i+3*nb_plc,1]<-"plc"
    tab_chrono[lim+i+3*nb_plc,2]<-"crd_imp"
    tab_chrono[lim+i+3*nb_plc,3]<-tabl_plac[i,"nom_plc"]
    tab_chrono[lim+i+3*nb_plc,4:(horiz+3)]<-fct_flux_crd_imp(tabl_plac[i,"nom_plc"],tabl_plac[i,"Valeur_t0"],(tabl_plac$An_tot[i]-tabl_plac$An_rest[i]),horiz,,)
  }
  lim<-dim(tab_chrono)[1]
  
  
  ### Recap ###
  #### calcul de l impot hors projets avec plc #####
  a<-tab_chrono %>% filter( type=="life"|type=="plc") %>% filter(sous.type=="revenu"|sous.type=="crd_imp"|sous.type=="part_imp" )
  QF<-apply(a %>% filter(sous.type=="revenu") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  part<-apply(a %>% filter(sous.type=="part_imp",sous.type_2=="hors projets") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  QF<-QF/part
  imp<-fct_flux_IR(QF)*part
  tab_chrono[lim+1,1]<-"impots"
  tab_chrono[lim+1,2]<-"IR"
  tab_chrono[lim+1,3]<-"hors_projets"
  tab_chrono[lim+1,4:(horiz+3)]<--imp+apply(a %>% filter(sous.type=="crd_imp") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  lim<-dim(tab_chrono)[1]
  
  ###### calcul de l'impot paye en considerant les projets #####
  ## part imposable avec projets avec plc 
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"part_imp"
  tab_chrono[lim+1,3]<-"avec projets"
  nb_part<-tab_chrono%>%filter(type=="life",sous.type=="part_imp",sous.type_2=="hors projets") %>% select(-type,-sous.type,-sous.type_2)
  nb_part<-nb_part+apply(tab_chrono%>%filter(type=="projets",sous.type=="part_imp") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  tab_chrono[lim+1,4:(horiz+3)]<-nb_part
  lim<-dim(tab_chrono)[1]
  # calcul de l'impot
  a<-tab_chrono %>% filter( type=="life"|type=="plc"|type=="projets") %>% filter(sous.type=="revenu"|sous.type=="crd_imp"|sous.type=="part_imp" )
  QF<-apply(a %>% filter(sous.type=="revenu") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  # abattement pour frais de 10%
  QF<-QF*0.9
  QF<-QF/nb_part
  imp<-fct_flux_IR(QF)*part
  tab_chrono[lim+1,1]<-"impots"
  tab_chrono[lim+1,2]<-"IR"
  tab_chrono[lim+1,3]<-"final"
  tab_chrono[lim+1,4:(horiz+3)]<--imp+apply(a %>% filter(sous.type=="crd_imp") %>% select(-type,-sous.type,-sous.type_2),2,sum)
  lim<-dim(tab_chrono)[1]
  
  # ajout du taux marginal d'impot
  taux_marg<-array(0,length(QF))
  for (z in 1:length(tab_IR[,1])) {
    taux_marg[which(QF>tab_IR[z,1])]<-tab_IR[z,2]
  }
  tab_chrono[lim+1,1]<-"impots"
  tab_chrono[lim+1,2]<-"taux_marg_IR"
  tab_chrono[lim+1,3]<-"final"
  tab_chrono[lim+1,4:(horiz+3)]<-taux_marg
  lim<-dim(tab_chrono)[1]
  
  ####### flux hors impots, hors projets #####
  ############### calcul nombre part conso
  if (hist_$revenu[[1]]$nb_sal==1) {
    compte_pers<- rep(Part_conso_foyer[1],horiz)
  } else {compte_pers<- rep((Part_conso_foyer[1]+Part_conso_foyer[2]),horiz)} # comptage Oxford (non OCDE)
  list<- as_tibble(hist_$fisc[[1]]$age_enf)[[1]]
  list<-as.data.frame(list[[1]])
  list<-list[which(list!=0),]
  if (length(list)!=0) {
    for (i in 1:length(list)) {
      evol_age<-seq(horiz)+list[i]-1
      compte_enf<-rep(0,horiz)
      compte_enf[evol_age<=14]<-Part_conso_foyer[3]
      compte_enf[evol_age>14]<-Part_conso_foyer[4]
      compte_enf[evol_age>20]<-0
      compte_pers<-compte_pers+compte_enf
    }
  }
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"part_conso"
  tab_chrono[lim+1,3]<-"hors projets"
  tab_chrono[lim+1,4:(horiz+3)]<-compte_pers
  lim<-dim(tab_chrono)[1]
  
  # depenses courantes hors projets #
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"hors_imp"
  tab_chrono[lim+1,3]<-"depenses hors projets"
  Annuite<-hist_$fiche[[1]]$annui_immo
  taux_eparg<-as.numeric(as.data.frame(hist_$revenu[[1]])$taux_eparg)
  impot_horsprojet<-tab_chrono%>%filter(type=="impots",sous.type=="IR",sous.type_2=="hors_projets")%>% select(-type,-sous.type,-sous.type_2)
  if (Loyer!=0) { # locataire
    taux_depense<--(sal1+sal2+montant+sum(hist_$plc[[1]]$Revenu)-taux_eparg-Loyer-sum(hist_$plc[[1]]$Annuite[-1])+impot_horsprojet[1])
  } else { #proprio
    taux_depense<--(sal1+sal2+montant+sum(hist_$plc[[1]]$Revenu)-taux_eparg-sum(hist_$plc[[1]]$Annuite)+impot_horsprojet[1])
  }
  depense_pers<--as.numeric(taux_depense/compte_pers[1])
  chrono_depense<- compte_pers*depense_pers
  
  if (hist_$revenu[[1]]$box_evol_sal==1) { # depense stable
    tab_chrono[lim+1,4:(horiz+3)]<--chrono_depense
  } else { # depense evolue comme salaire
    evol_sal<-tab_chrono[1,4:(horiz+3)]+tab_chrono[2,4:(horiz+3)]
    evol_sal<- evol_sal[1:horiz]*as.numeric(1/evol_sal[1])
    tab_chrono[lim+1,4:(horiz+3)]<--chrono_depense*evol_sal
  }
  lim<-dim(tab_chrono)[1]
  
  
  # Epargne libre #
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"hors_imp"
  tab_chrono[lim+1,3]<-"Epargne libre hors projets"
  a<-tab_chrono%>%filter(type!="projets")
  life<- a %>% filter(type=="life" & sous.type!="part_imp" & sous.type_2!="Epargne libre hors projets") %>%
    select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  plc<-a%>%filter(type=="plc"& sous.type!="crd_imp") %>%
    select(-type,-sous.type,-sous.type_2)%>%summarise_all(sum)
  impot<-a%>%filter(type=="impots"&sous.type=="IR"&sous.type_2=="hors_projets") %>% 
    select(-type,-sous.type,-sous.type_2)
  tab_chrono[lim+1,4:(horiz+3)]<--(life+plc+impot)
  # Verif: round(apply(tab_chrono[1:5,4:(horiz+3)],2,sum)+apply(tab_chrono[c(24,29),4:(horiz+3)],2,sum),4)
  lim<-dim(tab_chrono)[1]
  
  ####### flux hors impots, avec projets
  # depenses courantes avec projets #
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"hors_imp"
  tab_chrono[lim+1,3]<-"depenses avec projets"
  compte_pers<-compte_pers+tab_chrono%>%filter(type=="projets",sous.type=="part_conso")%>%select(-type,-sous.type,-sous.type_2)%>% summarise_all(sum)
  chrono_depense<- compte_pers*depense_pers
  if (hist_$revenu[[1]]$box_evol_sal==1) { # depense stable
    tab_chrono[lim+1,4:(horiz+3)]<--chrono_depense
  } else { # depense evolue comme salaire
    evol_sal<-tab_chrono[1,4:(horiz+3)]+tab_chrono[2,4:(horiz+3)]
    evol_sal<- evol_sal[1:horiz]*as.numeric(1/evol_sal[1])
    tab_chrono[lim+1,4:(horiz+3)]<--chrono_depense*evol_sal
  }
  lim<-dim(tab_chrono)[1]
  # Epargne libre projets deduits#
  a<-bind_rows(
    tab_chrono%>%filter(type=="life",sous.type=="hors_imp",sous.type_2=="depenses avec projets")
    ,tab_chrono%>%filter(type=="impots",sous.type=="IR",sous.type_2=="final")
    ,tab_chrono%>%filter(sous.type=="principal")
    ,tab_chrono%>%filter(sous.type=="interet")
    ,tab_chrono%>%filter(sous.type_2=="loyer")
  ) %>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  b<-tab_chrono%>%filter(sous.type=="revenu") %>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # projet hors_imp
  c<-tab_chrono %>% filter(type=="projets",sous.type=="hors_imp")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"hors_imp"
  tab_chrono[lim+1,3]<-"Epargne libre avec projets"
  tab_chrono[lim+1,4:(horiz+3)]<--(b+a+c)
  lim<-dim(tab_chrono)[1]
  
  ###### cacul du taux_endt et credit sup max possible avec projet ######
  taux_endet_max<-0.33
  taux_compt_div<-0.75
  # revenu
  a<-tab_chrono %>% filter(sous.type=="revenu",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # loyer recu
  b<-tab_chrono %>% filter(sous.type=="revenu",type!="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  b<- taux_compt_div * b
  # pension recue 
  c<-0
  # charges
  # loyer verse
  d<- tab_chrono %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # credit en cours
  e <- tab_chrono %>% filter(sous.type=="principal" ) %>% select(-type,-sous.type,-sous.type_2)
  # on retire grossierement l'apport s'il existe
  for (i in 1:length(e[,1])) {
    if ( length( which(e[i,]!=0 ) )>=2 )  {
      e[i,which(e[i,]!=0)[1] ] <-e[i, (which(e[i,]!=0)[1]+1) ]
    }}
  e <- e %>% summarise_all(sum)
  f<-tab_chrono %>% filter( sous.type=="interet")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  
  # pension versee
  g<-0
  
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"taux_endt"
  tab_chrono[lim+1,3]<-"avec projets"
  tab_chrono[lim+1,4:(horiz+3)]<- -(d+e+f+g)/(a+b+c)
  lim<-dim(tab_chrono)[1]
  
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"credit sup"
  tab_chrono[lim+1,3]<-"avec projets"
  tab_chrono[lim+1,4:(horiz+3)]<- taux_endet_max*(a+b+c) + (d+e+f) # 33% *revenu-charges
  lim<-dim(tab_chrono)[1]
  
  
  ###### cacul du taux_endt et credit sup max possible avec projet ######
  taux_endet_max<-0.33
  taux_compt_div<-0.75
  # revenu
  a<-tab_chrono %>% filter(type!="projets",sous.type=="revenu",type=="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # loyer recu
  b<-tab_chrono %>% filter(type!="projets",sous.type=="revenu",type!="life")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  b<- taux_compt_div * b
  # pension recue 
  c<-0 # contabilisé dans les revenus
  # charges
  # loyer verse
  d<- tab_chrono %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  # credit en cours
  e <- tab_chrono %>% filter(type!="projets",sous.type=="principal" ) %>% select(-type,-sous.type,-sous.type_2)
  # on retire grossierement l'apport s'il existe
  for (i in 1:length(e[,1])) {
    if ( length( which(e[i,]!=0 ) )>=2 )  {
      e[i,which(e[i,]!=0)[1] ] <-e[i, (which(e[i,]!=0)[1]+1) ]
    }}
  e <- e %>% summarise_all(sum)
  
  f<-tab_chrono %>% filter(sous.type=="interet")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  
  # pension versee
  g<-0 # contabilisé dans les revenus
  
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"taux_endt"
  tab_chrono[lim+1,3]<-"hors projets"
  tab_chrono[lim+1,4:(horiz+3)]<- -(d+e+f+g)/(a+b+c)
  lim<-dim(tab_chrono)[1]
  
  tab_chrono[lim+1,1]<-"life"
  tab_chrono[lim+1,2]<-"credit sup"
  tab_chrono[lim+1,3]<-"hors projets"
  tab_chrono[lim+1,4:(horiz+3)]<- taux_endet_max*(a+b+c) + (d+e+f) # 33% *revenu-charges
  lim<-dim(tab_chrono)[1]
  #######################
  # dim(tab_chrono)
  
  
  return(tab_chrono)
}
