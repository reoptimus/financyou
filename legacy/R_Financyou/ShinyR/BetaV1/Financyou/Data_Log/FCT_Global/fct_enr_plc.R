############################
# fonction d'ecriture des ajouts ds user_projets
table_modif5<- function (hist_,data_plc, ...) {
  
  tab_plc_user<-as.data.frame(hist_$plc[[1]])
  # str(tab_plc_user)
  # data_plc<-c("6","Pinel","100000","1000","1.2","15","20","800")
  
  # mise en forme de la nouvelle ligne
  data_mef<-tab2_plc[as.character(data_plc[1]),16:23]
  # ecriture des donnees ds les lettres dans l'ordre d arrivee
  Text<-paste0("nom_plc","<-'",data_plc[2],"'" )
  eval( parse ( text = Text))
  for (i in 3:(length(data_plc))) {
    Text<-paste0(letters[i-2],"<-",data_plc[i])
    eval( parse(text=Text) )
  }
  
  
  Valeur_t0<-as.numeric(eval(parse(text=as.character(data_mef$Valeur_t0))))
  Annuite<-as.numeric(eval(parse(text=as.character(data_mef$Annuite))))
  Taux<-as.numeric(eval(parse(text=as.character(data_mef$Taux))))
  An_rest<-as.numeric(eval(parse(text=as.character(data_mef$An_rest))))
  An_tot<-as.numeric(eval(parse(text=as.character(data_mef$An_tot))))
  Revenu<-as.numeric(eval(parse(text=as.character(data_mef$Revenu))))
  sous_type<-as.character(eval(parse(text=as.character(data_mef$Sous_type)  ) )  )
  type<-as.character(data_mef$type)
  if (Taux==0) { #pas de crd
    V0_net<-Valeur_t0
  } else { # crd
  V0_net<-Valeur_t0-(Annuite/Taux)*(1-(1+Taux)^(-An_rest))
  }
  # ref de tranche du GSE++
  ref_GSE_part1<- as.numeric(eval(parse(text=as.character(tab2_plc[data_plc[1],]$Part_1))))
  ref_GSE_Tr1<- as.character(tab2_plc[data_plc[1],]$Equiv_GSE1)
  ref_GSE_part2<- as.numeric(eval(parse(text=as.character(tab2_plc[data_plc[1],]$Part_2))))
  ref_GSE_Tr2<- as.character(tab2_plc[data_plc[1],]$Equiv_GSE2)
  a<-c(ref_GSE_part1,ref_GSE_Tr1,ref_GSE_part2,ref_GSE_Tr2)

  # ajout au tableau des projets
  tab_plc_new<-c(nom_plc,type,sous_type,Valeur_t0,Annuite,Taux,An_rest,An_tot,Revenu,V0_net,a) #,ref_GSE
  tab_plc_new<-t(tab_plc_new)
  tab_plc_new<-as.data.frame(tab_plc_new,stringsAsFactors = FALSE)
  names(tab_plc_new)<-c("nom_plc","type","sous_type","Valeur_t0","Annuite","Taux","An_rest","An_tot","Revenu","V0_net","Part_Tr_GSE1","nom_Tr_GSE1","Part_Tr_GSE2","nom_Tr_GSE2")
  tab_plc_new[c("Valeur_t0","Annuite","Taux","An_rest","An_tot","Revenu","V0_net","Part_Tr_GSE1","Part_Tr_GSE2")]<-as.numeric(tab_plc_new[c("Valeur_t0","Annuite","Taux","An_rest","An_tot","Revenu","V0_net","Part_Tr_GSE1","Part_Tr_GSE2")])
  # tab_plc_user<-tab_plc_new
  tab_plc_user<-rbind(tab_plc_user,tab_plc_new)

  # enregistrement
  hist_[,"plc"]<-nest(tab_plc_user,data = everything())
  return(hist_)
}

############################
# fonction d'ecriture ds user_projets apres Delete d'une ligne
table_modif5_bis<- function (hist_,tab_plc_user, ...) {
  # tab_plc_user<-df_plc
  # enregistrement
  hist_[,"plc"]<-nest(tab_plc_user,data = everything())
  return(hist_)
}

##########################
# fonction enr dans plc des modif sur l immo
fct_enr_immo2plc<- function (hist_) {
 
  a<-as.data.frame(hist_$plc[[1]])
  a$V0_net<-as.numeric(a$V0_net)
  a[1,4:10]<-fct_plc_hab(hist_)
  a[1,1]<-"Votre logement"
  a[1,2]<-"Immobilier"
  a[1,3]<-"0"
  a[1,11]<-"1"
    a[1,12]<-"RimmoPropre"
    a[1,13]<-"0"
    a[1,14]<-"NULL"
  hist_[,"plc"]<-nest(a,data = everything())
  return(hist_)
}
##########################
# fonction de translation hab_user -> plc
fct_plc_hab<- function (hist_) {
  prop<-as.data.frame(hist_$fiche[[1]])$proprietaire
  fini<-as.data.frame(hist_$fiche[[1]])$finipayer
  V0<-as.data.frame(hist_$fiche[[1]])$Montantbien
  an_tot<-as.data.frame(hist_$fiche[[1]])$an_tot
  an_rest<-as.data.frame(hist_$fiche[[1]])$an_rest
  tau<-as.data.frame(hist_$fiche[[1]])$taux_crd_immo
  annui<-as.data.frame(hist_$fiche[[1]])$annui_immo
  #loyer<-as.data.frame(hist_$fiche[[1]])$Loyer

  if (prop==1) { #proprio
    if (fini==1) {
      V0_net<-V0
    } else {V0_net<-V0-(annui/tau)*(1-(1+tau)^(-an_rest))  }
    #loyer<-0
  } else { # locataire
    V0_net<-0
    V0<-0
  }
  return(c(V0,annui,tau,an_rest,an_tot,0,V0_net))
}

###########
################# Fonction enr plc pour projet immo
###########
# fonction d'ecriture des ajouts ds user_projets
table_modif_plc_immo<- function (hist_,data_plc,ligne_proj, ...) {
  
  # str(tab_plc_user)
  # data_plc<-c("6"   ,   "Pinel" , "261000", "-1228" , "1.4"  ,  "16"  ,   "27"  ,   "440")
  # data_plc<-plc_proj
  # ligne_proj<-4
  
  # mise en forme de la nouvelle ligne
  data_mef<-tab2_plc[as.character(data_plc[1]),16:23]
  # ecriture des donnees ds les lettres dans l'ordre d arrivee
  Text<-paste0("nom_plc","<-'",data_plc[2],"'" )
  eval( parse ( text = Text))
  for (i in 3:(length(data_plc))) {
    Text<-paste0(letters[i-2],"<-",data_plc[i])
    eval( parse(text=Text) )
  }
  
  
  Valeur_t0<-as.numeric(eval(parse(text=as.character(data_mef$Valeur_t0))))
  Annuite<-as.numeric(eval(parse(text=as.character(data_mef$Annuite))))
  Taux<-as.numeric(eval(parse(text=as.character(data_mef$Taux))))
  An_rest<-as.numeric(eval(parse(text=as.character(data_mef$An_rest))))
  An_tot<-as.numeric(eval(parse(text=as.character(data_mef$An_tot))))
  Revenu<-as.numeric(eval(parse(text=as.character(data_mef$Revenu))))
  sous_type<-as.character(eval(parse(text=as.character(data_mef$Sous_type)  ) )  )
  type<-as.character(data_mef$type)
  
  # ref de tranche du GSE++
  ref_GSE_part1<- as.numeric(eval(parse(text=as.character(tab2_plc[data_plc[1],]$Part_1))))
  ref_GSE_Tr1<- as.character(tab2_plc[data_plc[1],]$Equiv_GSE1)
  ref_GSE_part2<- as.numeric(eval(parse(text=as.character(tab2_plc[data_plc[1],]$Part_2))))
  ref_GSE_Tr2<- as.character(tab2_plc[data_plc[1],]$Equiv_GSE2)
  a<-c(ref_GSE_part1,ref_GSE_Tr1,ref_GSE_part2,ref_GSE_Tr2)
  
  # ajout au tableau des projets
  tab_plc_new<-c(nom_plc,type,sous_type,Valeur_t0,Annuite,Taux,An_rest,An_tot,Revenu,ligne_proj,a) #,ref_GSE
  tab_plc_new<-t(tab_plc_new)
  tab_plc_new<-as.data.frame(tab_plc_new,stringsAsFactors = FALSE)
  names(tab_plc_new)<-c("nom_plc","type","sous_type","Valeur_t0","Annuite","Taux","An_rest","An_tot","Revenu","ligne_proj","Part_Tr_GSE1","nom_Tr_GSE1","Part_Tr_GSE2","nom_Tr_GSE2")
  tab_plc_new[c("Valeur_t0","Annuite","Taux","An_rest","An_tot","Revenu","ligne_proj","Part_Tr_GSE1","Part_Tr_GSE2")]<-as.numeric(tab_plc_new[c("Valeur_t0","Annuite","Taux","An_rest","An_tot","Revenu","ligne_proj","Part_Tr_GSE1","Part_Tr_GSE2")])
  # tab_plc_user<-tab_plc_new
  if (length(as.data.frame(hist_$plc_immo[[1]])[1,1])==0) { # pas de projet immo en cours
    tab_plc_user<-tab_plc_new
  } else { # projet immo deja present
    tab_plc_user<-as.data.frame(hist_$plc_immo[[1]])
    tab_plc_user<-rbind(tab_plc_user,tab_plc_new)
  }
  
  # enregistrement
  hist_[,"plc_immo"]<-nest(tab_plc_user,data = everything())
  return(hist_)
}

table_modif_plc_immo_bis<- function (hist_,tab_plc_user, ...) {
  
  # enregistrement
  hist_[,"plc_immo"]<-nest(tab_plc_user,data = everything())
  return(hist_)
}
