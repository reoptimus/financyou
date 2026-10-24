table_modif2<- function (session_pseudo,passwd="",hist_,slider_loyer,check_box1,check_box2,slider_immo,slider_immo_antot,slider_immo_anrest,slider_immo_taux,slider_immo_mens) {
  
  # mise en forme des inputs
  session_pseudo<-as.character(session_pseudo) # session_pseudo<-"toto"
  passwd<-as.character(passwd)                # passwd<-"passtoto"
  check_box1<-as.numeric(check_box1)
  check_box2<-as.numeric(check_box2)
  slider_immo<-as.numeric(slider_immo)*1000
  slider_immo_taux<-as.numeric(slider_immo_taux)*0.01
  slider_loyer<-as.numeric(slider_loyer)*12
  slider_immo_mens<-as.numeric(slider_immo_mens)*12
  
  ####################
  # ecriture immo
  ##########
  # verifications
  if (check_box1==1){ # propriÃÂ©taire
    slider_loyer<-0
    if (check_box2==2) { # pas fini de payer
    } else { # fini de payer ou case vide
      slider_immo_anrest<-0
      slider_immo_taux<-0
      slider_immo_antot<-0
      slider_immo_mens<-0
    } #end if
  } else { # locataire
    check_box2<-1
    slider_immo_anrest<-0
    slider_immo_taux<-0
    slider_immo_antot<-0
    slider_immo<-0
    slider_immo_mens<-0
  } # fin if ecriture immo
  
  # slider_loyer<-10000
  # check_box1<-1
  # check_box2<-2
  # slider_immo<-400000
  # slider_immo_antot<-20
  # slider_immo_anrest<-15
  # slider_immo_taux<-0.02
  # slider_immo_mens<-800
  # ligne<-c(1:4)
  
  b<-as.data.frame( t(c(slider_loyer,check_box1,check_box2,slider_immo,slider_immo_antot,slider_immo_anrest,slider_immo_taux,slider_immo_mens)) )
  names(b)<-c("Loyer","proprietaire","finipayer","Montantbien","an_tot","an_rest","taux_crd_immo","annui_immo")
  
  hist_[,"fiche"]<-nest(b,data = everything())
  return(hist_)
}
####################################################
# fonction d'ecriture des modifications "vos ressources"
table_modif2bis<- function (session_pseudo,passwd="",hist_,slider_sal,sal2,slider_epar,nb_sal,check_box_evol_sal) {
  
  # mise en forme des inputs
  session_pseudo<-as.character(session_pseudo) # session_pseudo<-"test"
  passwd<-as.character(passwd)                # passwd<-"passtest"
  slider_sal<-as.numeric(slider_sal)*1000
  slider_epar<-as.numeric(slider_epar)*1000
  nb_sal<-as.numeric(nb_sal)
  check_box_evol_sal<-as.numeric(check_box_evol_sal)
  sal2<-as.numeric(sal2)*1000
  
  # slider_sal<-80000
  # slider_epar<-0.15
  # slider_evol_sal<-0.05
  # slider_evol_sal2<-0.02
  # check_box_evol_sal<-1


  res_retraite1<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$res_retraite1))
  res_retraite2<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$res_retraite2))
  metier1<-as.character(as.data.frame(hist_$revenu[[1]])$metier1)
  metier2<-as.character(as.data.frame(hist_$revenu[[1]])$metier2)
  slider_evol_sal<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$evol_sal))
  slider_evol_sal2<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$evol_sal2))
  
  d<-as.data.frame(t(c(slider_sal,slider_epar,slider_evol_sal,slider_evol_sal2,check_box_evol_sal,nb_sal,sal2,res_retraite1,res_retraite2)),stringsAsFactors=FALSE)
  names(d)<-c("Net_imposable","taux_eparg","evol_sal","evol_sal2","box_evol_sal","nb_sal","sal2","res_retraite1","res_retraite2")
  d<-cbind(d,metier1,metier2,stringsAsFactors=FALSE)
  # str(d)
  hist_[,"revenu"]<-nest(d,data=everything())
  return(hist_)
}
####################################################
# fonction d'ecriture des modifications "socio pro"
table_modif2ter<- function (session_pseudo,passwd="",hist_,slider_evol_sal,slider_evol_sal2,res_retraite1,res_retraite2,metier1,metier2) {
  
  # mise en forme des inputs
  session_pseudo<-as.character(session_pseudo) # session_pseudo<-"test"
  passwd<-as.character(passwd)                # passwd<-"passtest"
  slider_evol_sal<-as.numeric(slider_evol_sal)*0.01
  slider_evol_sal2<-as.numeric(slider_evol_sal2)*0.01
  res_retraite1<-as.numeric(res_retraite1)
  res_retraite2<-as.numeric(res_retraite2)
  metier1<-as.character(metier1) 
  metier2<-as.character(metier2)

  slider_sal<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$Net_imposable))
  sal2<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$sal2))
  slider_epar<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$taux_eparg))
  nb_sal<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$nb_sal))
  check_box_evol_sal<-as.numeric(as.character(as.data.frame(hist_$revenu[[1]])$box_evol_sal))
  # nb_sal<-1
  # sal2<-30000
  # res_retraite1<-14
  # res_retraite2<-10
  # metier1<-"salarie"
  # metier2<-"salarie"
  d<-as.data.frame(t(c(slider_sal,slider_epar,slider_evol_sal,slider_evol_sal2,check_box_evol_sal,nb_sal,sal2,res_retraite1,res_retraite2)),stringsAsFactors=FALSE)
  names(d)<-c("Net_imposable","taux_eparg","evol_sal","evol_sal2","box_evol_sal","nb_sal","sal2","res_retraite1","res_retraite2")
  d<-cbind(d,metier1,metier2,stringsAsFactors=FALSE)
  # str(d)
  hist_[,"revenu"]<-nest(d,data=everything())
  return(hist_)
}