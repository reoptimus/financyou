############################
# fonction d'ecriture des ajouts ds user_projets
table_modif1<- function (session_pseudo,passwd,hist_,data_proj, ...) {
  
  # data_proj<-c("11","test","18382","0")
  # data_proj<-c("5"    ,    "Test bbc" ,"19058"   , "17"  ,     "1"   ,     "14.5")
  # data_proj<-c("3"  ,        "nom_projet" ,"20423") # baby
  # data_proj<-c("14"  ,  "Pinel" ,"22263" ,"261"  , "586" ,  "1.4"  , "16"  ,  "51" )
  
  # mise en forme de la nouvelle ligne
  data_mef<-tab2[as.character(data_proj[1]),18:23]
  # tabl proj avant modif
  tab_proj_user<-as.data.frame(hist_[,"projets"][[1]])
  
  # ecriture des donnees ds les lettres dans l'ordre d arrivee
  Text<-paste0("nom_projet","<-'",data_proj[2],"'" )
  eval( parse ( text = Text))
  for (i in 3:(length(data_proj))) {
    Text<-paste0(letters[i-2],"<-",data_proj[i])
    eval( parse(text=Text) )
  }
  ###### mise en forme des variables ###########
  if (length(data_proj)>=5) {
  Montant<-b*1000
  Taux_crd_immo<-d*0.01
  }
  andebut<-as.Date(as.numeric(eval(parse(text=as.character(data_mef$andebut)))),origin= as.Date("01/01/1970", format="%d/%m/%Y"))
  dist_debut<- ceiling(((andebut - as.Date(format(Sys.Date(), "%Y-%m-%d")))/365)[[1]] )
  mdebut<-as.numeric(eval(parse(text=as.character(data_mef$mdebut))))
  if (as.character(data_mef$duree)!="0") { # sil existe deux date dans le slider 1
    duree<-eval(parse(text=as.character(data_mef$duree)))
    duree<-ceiling(as.numeric(duree)/365)
  } else {
    duree<-0
  }
  mvers<-as.numeric(eval(parse(text=as.character(data_mef$mvers))))
  msortie<-as.numeric(eval(parse(text=as.character(data_mef$msortie))))
  pente<-as.numeric(eval(parse(text=as.character(data_mef$pente))))

  # print(list(andebut,mdebut,mvers,duree,msortie,pente))
  source(file="Data_Log/FCT_Global/Exp_proj_hist.R")
  
  # split entre le proj simple et les projets immo
if ( tab2[as.character(data_proj[1]),"groupe"]=="immo" ) { # c'est un projet immobilier a traiter comme un plc
    
  ##### definition des 5 chrono pour l'immo ####
  chrono_projet_revenu<- Exp_fin(horiz,andebut,0,msortie,horiz,0,0)
  chrono_projet_part_imp<-array(rep(0,horiz+1),dim=c(1,(horiz+1)))
  type_niche<-as.character(tab2[as.character(data_proj[1]),"Credits_impots"])
  chrono_projet_crd_imp<- t(as.matrix(fct_flux_crd_imp(type_niche,Montant,0,(horiz+1),1,dist_debut)))
  # dispatch du credit
  
  crd<-Flux_crd(horiz+1,mvers,Taux_crd_immo,duree)
  chrono_projet_principal<- (Exp_fin(horiz,andebut,mdebut,0,0,0,0)+c(rep(0,dist_debut), crd[[1]] )[1:(horiz+1)])
  chrono_projet_epar<- t(as.matrix(  c(rep(0,dist_debut), crd[[2]] )[1:(horiz+1)] ))
  # part de conso nulle
  chrono_projet_part_conso<-array(rep(0,horiz+1),dim=c(1,horiz+1))
  ########## equiv var des plc ###############
  Valeur_t0<-as.character(ceiling(Montant))
  Annuite<-as.character(ceiling(mvers/12))
  Taux<-as.character(Taux_crd_immo*100)
  An_rest<-as.character(duree)
  An_tot<-as.character(duree+dist_debut)
  Revenu<-as.character(ceiling(msortie/12))
  V0_net<-"0"
  if (data_proj[1]==14) {plc_proj<-c("6",nom_projet,Valeur_t0,Annuite,Taux,An_rest,An_tot,Revenu)}
  if (data_proj[1]==15) {plc_proj<-c("5",nom_projet,Valeur_t0,Annuite,Taux,An_rest,An_tot,Revenu)}
  if (data_proj[1]==16) {plc_proj<-c("7",nom_projet,Valeur_t0,Annuite,Taux,An_rest,An_tot,Revenu)}
  hist_<- table_modif_plc_immo(hist_,plc_proj,(length(tab_proj_user$nom_projet)+1))
  # hist_$plc_immo
  
} else { # pas un projet immo
  
    # 2 calcul des series temporelles pour les differents type
  # impact sur l'epargne
  if (tab2[as.character(data_proj[1]),]$Impact_epargne=="Y") {
  chrono_projet_epar<- Exp_fin(horiz,andebut,mdebut,mvers,duree,msortie,pente) } else {
    chrono_projet_epar<-array(rep(0,horiz+1),dim=c(1,horiz+1))
  }
  #impact sur le revenu
  if (tab2[as.character(data_proj[1]),]$Impact_revenu=="Y") {
  chrono_projet_revenu<- Exp_fin(horiz,andebut,mdebut,mvers,duree,msortie,pente)  } else { 
    chrono_projet_revenu<-array(rep(0,horiz+1),dim=c(1,horiz+1))
  }
  # impact sur les parts imposables
  chrono_projet_part_imp<-array(rep(0,horiz+1),dim=c(1,horiz+1))
  chrono_projet_part_conso<-array(rep(0,horiz+1),dim=c(1,horiz+1))
  if (tab2[as.character(data_proj[1]),]$Evol_part_impot!="NULL") {
    chrono_projet_part_imp<-Exp_fin(horiz,andebut,0.5,0.5,18,0,0)
    # ajout de la part de conso
    evol_age<-seq(horiz)- round(((andebut-Sys.Date())/365)[[1]],0)
    evol_age<-apply(rbind(rep(0,horiz),evol_age),2,max)
    compte_enf<-rep(0,horiz)
    compte_enf[evol_age<=14&evol_age>0]<-Part_conso_foyer[3]
    compte_enf[evol_age>14]<-Part_conso_foyer[4]
    compte_enf[evol_age>20]<-0
    chrono_projet_part_conso<-t(as.matrix(compte_enf))
  } else {}
  
  # impact sur le credit d'impot
    chrono_projet_crd_imp<-array(rep(0,horiz+1),dim=c(1,horiz+1))
    if (tab2[as.character(data_proj[1]),]$Credits_impots!="NULL") {
      crd_imp<-as.numeric(tab2[as.character(data_proj[1]),]$Credits_impots)
      chrono_projet_crd_imp<-Exp_fin(horiz,andebut,mdebut*crd_imp,0,0,0,0)
    }
    
  # impact sur le principale dun credit immmo
    chrono_projet_principal<-array(rep(0,horiz+1),dim=c(1,horiz+1))
    ################
    
  }  # fin if si immo or not
  
  # ajout au tableau des projets
  #str(chrono_projet)
  tab_proj_new<-list(nom_projet,andebut,ceiling(-sum(chrono_projet_epar,chrono_projet_principal)),chrono_projet_revenu,chrono_projet_epar,chrono_projet_part_imp,chrono_projet_crd_imp,chrono_projet_principal,chrono_projet_part_conso)
  tab_proj_new<-t(tab_proj_new)
  tab_proj_new<-as.data.frame(tab_proj_new,stringsAsFactors = FALSE)
  names(tab_proj_new)<-c("nom_projet","andebut","mont_tot_proj","chrono_projet_revenu","chrono_projet_epar","chrono_projet_part_imp","chrono_projet_crd_imp","chrono_projet_principal","chrono_projet_part_conso")
  # str(tab_proj_new)

  tab_proj_new["nom_projet"]<-as.character(tab_proj_new["nom_projet"][[1]])
  tab_proj_new["andebut"]<-tab_proj_new["andebut"][[1]]
  tab_proj_new["mont_tot_proj"]<-as.numeric(tab_proj_new["mont_tot_proj"][[1]])
  tab_proj_new["chrono_projet_revenu"]<-nest(as.data.frame(tab_proj_new["chrono_projet_revenu"][[1]]),data = everything())
  tab_proj_new["chrono_projet_epar"]<-nest(as.data.frame(tab_proj_new["chrono_projet_epar"][[1]]),data = everything())
  tab_proj_new["chrono_projet_part_imp"]<-nest(as.data.frame(tab_proj_new["chrono_projet_part_imp"][[1]]),data = everything())
  tab_proj_new["chrono_projet_crd_imp"]<-nest(as.data.frame(tab_proj_new["chrono_projet_crd_imp"][[1]]),data = everything())
  tab_proj_new["chrono_projet_principal"]<-nest(as.data.frame(tab_proj_new["chrono_projet_principal"][[1]]),data = everything())
  tab_proj_new["chrono_projet_part_conso"]<-nest(as.data.frame(tab_proj_new["chrono_projet_part_conso"][[1]]),data = everything())
  # str(tab_proj_new)
  # as.data.frame((tab_proj_new$chrono_proj)[[1]])
  
  # tab_proj_user<-tab_proj_user[1:3,]
  # tab_proj_user <- tab_proj_new
  tab_proj_user<- rbind(tab_proj_user,tab_proj_new)
  
  # enregistrement
  hist_[,"projets"]<-nest(tab_proj_user,data = everything())
  return(hist_)
}

############################
# fonction d'ecriture ds user_projets apres Delete d'une ligne
table_modif1_bis<- function (session_pseudo,passwd,hist_,tab_proj_user,tab_proj_user_plc) {
  
  # enregistrement
  hist_[,"projets"]<-nest(tab_proj_user,data = everything())
  hist_[,"plc_immo"]<-nest(tab_proj_user_plc,data = everything())
  return(hist_)
}

