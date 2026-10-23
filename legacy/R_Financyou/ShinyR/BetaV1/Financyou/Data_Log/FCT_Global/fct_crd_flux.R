# cree le 11052020
# par Sebastien gallet
# Version 1.0
#
# Fonction de transformation crd en flux: principal , interet
########################

Flux_crd<- function (horiz,Annuite,Taux_crd_immo,An_rest) {
  # horiz
  # Annuite<-tabl_plac$Annuite[i]
  # Taux_crd_immo<-tabl_plac$Taux[i]
  # An_rest<-tabl_plac$An_rest[i]
  if (Taux_crd_immo==0) {
    a<-rep(0,horiz)
    a<-list(a,a)
  } else {
  # calcul des interet a payer
  # flux capital restant du
  Valeur_t0_Rest_crd<-Annuite*(1-(1+Taux_crd_immo)^(-(An_rest:0)))/Taux_crd_immo
  if (length(Valeur_t0_Rest_crd)<=horiz) {
    Valeur_t0_Rest_crd<-c(Valeur_t0_Rest_crd,rep(0,horiz-length(Valeur_t0_Rest_crd)))
    Annuite_chrono<-c(rep(Annuite,An_rest),rep(0,horiz-An_rest))
  } else {
    Valeur_t0_Rest_crd<-Valeur_t0_Rest_crd[1:horiz]
    Annuite_chrono<-rep(Annuite,horiz)
  }
  int_crd<-Taux_crd_immo*Valeur_t0_Rest_crd
  int_crd<-round(int_crd)
  # calcul du principal
  princip_crd<-Annuite_chrono-int_crd
  princip_crd<-round(princip_crd)
  
  a<-list(princip_crd,int_crd)
  }
  return(a)
}