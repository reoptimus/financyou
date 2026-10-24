###################
#
# Recalcul des revenus issus des plc immobilier
# en fonction du montant
#
###################

fct_recalcul_revenu<-function(nom_apport,montant,tab_chrono) {
  
  if (nom_apport=="RimmoPropre") { # on achete pour arreter de louer
    # nom_plc<-"Votre logement"
    # nom_invest<-"RimmoPropre"
    revenu<- (tab_chrono %>% filter(type=="life",sous.type=="hors_imp",sous.type_2=="loyer") %>% select(-type,-sous.type,-sous.type_2))
    revenu<- -revenu
    revenu<-max(revenu)
  }
  if (nom_apport=="RimmoPinel") { # on achete pour louer a une tierce
    # nom_plc<-"Pinel"
    # nom_invest<-"RimmoPinel"
    rdt_loc<-0.025
    retenu_loyer<-0.85
    revenu<- retenu_loyer*rdt_loc*montant #premier tour a 80000eur
  }
  if (nom_apport=="RimmoLoc") { # on achete pour louer a une tierce
    # nom_plc<-"Pinel"
    # nom_invest<-"RimmoPinel"
    rdt_loc<-0.04
    retenu_loyer<-0.85
    revenu<- retenu_loyer*rdt_loc*montant #premier tour a 80000eur
  } 
  
  if (nom_apport!="RimmoPropre" && nom_apport!="RimmoPinel" && nom_apport!="RimmoLoc") {revenu<-0}
  
  return(revenu)
}