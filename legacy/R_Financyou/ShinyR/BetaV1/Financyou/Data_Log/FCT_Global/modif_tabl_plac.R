##################################
#
# cree le 11/11/2020
# par SG
#
# ajouter les 1plc avec credit/contrainte en automatique a tabl_plac
#
##################################
#horiz=20
modif_tabl_plac<- function(tabl_placi,montant,annuite,tau,debut_optim,n,revenu,nom_plc) {

  # revenu<-0
  # nom_plc<-nom_invest
  tabl_placi<-add_row(tabl_placi)
  num_lig<-length(tabl_placi[,1])
  if (nom_plc=="RimmoPropre") {
    tabl_placi$nom_plc[length(tabl_placi[,1])]<-"Votre logement"
  } else {
    tabl_placi$nom_plc[length(tabl_placi[,1])]<-paste0("ajout_",nom_plc)
  }
  
  tabl_placi$type[length(tabl_placi[,1])]<-"Immobilier"
  tabl_placi$sous_type[num_lig]<-"ajout"
  tabl_placi$Valeur_t0[num_lig]<-montant
  tabl_placi$Annuite[num_lig]<-annuite
  tabl_placi$Taux[num_lig]<-tau
  tabl_placi$An_rest[num_lig]<-n
  tabl_placi$An_tot[num_lig]<-n+debut_optim
  tabl_placi$Revenu[num_lig]<-revenu
  tabl_placi$V0_net[num_lig]<-montant
  tabl_placi$Part_Tr_GSE1[num_lig]<-1
  tabl_placi$nom_Tr_GSE1[num_lig]<-nom_plc
  tabl_placi$Part_Tr_GSE2[num_lig]<-0
  tabl_placi$nom_Tr_GSE2[num_lig]<-"NULL"

  return(tabl_placi)
}
