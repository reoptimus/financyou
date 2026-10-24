#####################################
# fonction de reconnaissance des pseudo et creation de compte
table_proj<- function (session_pseudo,passwd="NNNNNNNNN") {
  
  # session_pseudo<-"doudoune"  session_pseudo<-"test"
  # passwd<-"[retire]"      passwd<-"passtest" 
  test_pass<-(paste0(BDD_List$pseudo,BDD_List$pass)==paste0(session_pseudo,passwd))
  # BDD<-BDD[1:2,] # remise a zero de BDD
  if (passwd!="" & passwd!="0") {
    if (sum(test_pass)==FALSE) { # user pas retrouve
      if (sum(BDD_List$pseudo==session_pseudo)>0) {# pas bon passwd
        hist_<-NULL # un messaage d erreur en shinyalert (ici)
      } else {# pas connu-> creation 
        # on cree une nouvelle ligne dans BDD_List
        BDD_List$ID<-as.numeric(as.character(BDD_List$ID))
        BDD_List$pseudo<-as.character(BDD_List$pseudo)
        BDD_List$pass<-as.character(BDD_List$pass)
        BDD_List<-rbind(BDD_List,BDD_List[2,])
        
        # a<-array("",dim=dim(BDD_List))
        # for (i in 1:3) {
        #   a[,i]<-BDD_List[,i]
        # }
        # a<-as.data.frame(a,stringsAsFactors=FALSE)
        # colnames(a)<-colnames(BDD_List)
        # BDD_List<-a
        
        BDD_List[length(BDD_List$pseudo),1]<-session_pseudo
        BDD_List[length(BDD_List$pseudo),2]<-passwd
        BDD_List[length(BDD_List$pseudo),3]<-as.numeric(BDD_List[length(BDD_List$pseudo)-1,3])+1
        # BDD_List<-BDD_List[1:2,]
        save(BDD_List,file=paste0(reptravail,chemin,"Data_Log/","BDD_List.Rda"))
        saveData(outputDir,"BDD_List.Rda")
        # chargement d'un profil basique
        var_base<-"F_100002"
        loadData(outputDir,paste0(var_base,".Rda"))
        load(file=paste0(reptravail,chemin,"Data_Log/",var_base,".Rda"))
        user_projets$pseudo<-session_pseudo
        user_projets$pass<-passwd
        # ecriture du nouveau profil
        # user_projets<-hist_
        var_base<-paste0("F_",BDD_List[length(BDD_List$pseudo),3])
        save(user_projets,file=paste0(reptravail,chemin,"Data_Log/",var_base,".Rda"))
        saveData(outputDir,paste0(var_base,".Rda"))
        hist_<-user_projets
      } # fin de la creation
    } else { if (sum(test_pass)==1) {#trouve
      ID_name<-paste0("F_",BDD_List[which(test_pass==TRUE),3])
      loadData(outputDir,paste0(ID_name,".Rda"))
      load(file=paste0(reptravail,chemin,"Data_Log/",ID_name,".Rda"))
      hist_<-user_projets
    }else { #pb plusieur fois meme user
      hist_<-NULL
    } 
    }
    return( hist_ )
  } else {
    hist_<-NULL
  }
  
} # end function table_proj

#########################################################
# fonction pour sauvegarder les projets: 2 cas de figures
# - creation: table_modif1
# - suppression d'une ligne: table_modif1bis
source(file="Data_Log/FCT_Global/fct_enr_proj.R")
#########################################################

#########################################################
# fonction d'ecriture des modifications des slider "en vrac" Vous (autre que placements)
# table_modif2,bis et ter , dépendent de l'ouverture des bsPanel
source(file="Data_Log/FCT_Global/fct_enr_vous_vrac.R")
#########################################################

#########################################################
# fonction pour sauvegarder les placements: 2 cas de figures
# - creation: table_modif5
# - suppression d'une ligne: table_modif5bis
source(file="Data_Log/FCT_Global/fct_enr_plc.R")
#########################################################

#########################################################
# fonction pour sauvegarder les positions des switches
source(file="Data_Log/FCT_Global/fct_enr_switch.R")
#########################################################


####################################################
# fonction d'ecriture des modifications des switch
table_modif3<- function (session_pseudo,passwd="",hist_, switch_risk_max,switch_risk_mid,switch_risk_min,switch_trend_max,switch_trend_mid,switch_trend_min) {
  # input$switch_risk_max,input$switch_risk_mid,input$switch_risk_min,input$switch_trend_max,input$switch_trend_mid,input$switch_trend_min
  # switch_risk_max<-TRUE
  # switch_risk_mid<-FALSE
  # switch_risk_min<-FALSE
  # switch_trend_max<-TRUE
  # switch_trend_mid<-FALSE
  # switch_trend_min<-FALSE
  
  # ecriture de la position des input$switch_risk_max
  if (switch_risk_max==TRUE) {
    risk<-3 } else { if (switch_risk_mid==TRUE) {
      risk<-2} else {risk<-1}}
  if (switch_trend_max==TRUE) {
    trend<-3 } else { if (switch_trend_mid==TRUE) {
      trend<-2} else {trend<-1}}
  c<-as.data.frame(t(c(trend,risk)),stringsAsFactors=FALSE)
  names(c)<-c("anticip","profilRisk")
  c<-nest(c,data=c("anticip","profilRisk"))
  # c[[1]]
  
  hist_[,"avers"]<-c
  return(hist_)
}

####################################################
# fonction d'ecriture des modifications "fisc"
table_modif4<- function (session_pseudo,passwd="",hist_,age_enf,pension,mont_pens) {
  
  # age_enf<- c(0,0,0,0,4,10)
  # pension<-"recue"
  # mont_pens<-"700"
  # mise en forme des inputs
  session_pseudo<-as.character(session_pseudo) # session_pseudo<-"test"
  passwd<-as.character(passwd)                # passwd<-"passtest"
  age_enf<-as.data.frame(age_enf)
  pension<-as.character(pension)
  mont_pens<-as.numeric(as.character(mont_pens))
  
  d<-as.data.frame(t(c(nest(age_enf,data=everything()),pension,mont_pens)))
  names(d)<-c("age_enf","pension","mont_pens")
  # str(d)
  hist_[,"fisc"]<-nest(d,data=everything())
  # print(hist_[,"fisc"][[1]]$age_enf)
  # user_projets<-hist_
  return(hist_)
}