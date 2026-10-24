# cree le 11052020
# par sebastien gallet
# FINANCYOU
#
# fonction de calcul du flux du credit d'impot en fonction du type de placement
###########################


fct_flux_crd_imp<- function (type_niche,montant_aujourd,an_passe,horiz,facteur=1,decal=0) {
  # type_niche<-tabl_plac[14,"nom_plc"] # type_niche = nom_invest
  # montant_aujourd<-montant
  # an_passe<-(tabl_plac$An_tot[i]-tabl_plac$An_rest[i]) # an_passe=0
  
  # facteur: permettant d etablir le lien entre le prix aujourd'hui et le prix d achat
  # decal: decalage pour le demarrage du plc # decal =debut_optim
  
  ligne<-which(tab2_crd_imp$Type==type_niche)
  if (sum(tab2_crd_imp$Type==type_niche)==FALSE) {
    flux_crd_imp<-rep(0,horiz)
  } else {
    crd_an<-tab2_crd_imp$Rabais[ligne] * min( montant_aujourd*facteur,tab2_crd_imp$plafond[ligne])
    an_rest<-tab2_crd_imp$Lissage[ligne]-an_passe
      if (decal==0) {
      flux_crd_imp<-c(rep(crd_an,an_rest), rep(0,horiz-an_rest)) } else {
      flux_crd_imp<-c(rep(0,decal),rep(crd_an,min(an_rest,horiz-decal) ), rep(0,max(0,horiz-an_rest-decal+1)))
      }
  }
  # length(flux_crd_imp)
  return(flux_crd_imp[1:horiz])
}