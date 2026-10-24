# cree le 11052020
# par sebastien gallet
# FINAncyou
#
# fct de calcul de l'IR
########################

fct_flux_IR<-function(QF) {
  QFi<-QF
  imp<-QF*0
  tab_IR$Revenu.IR<-as.numeric(as.character(tab_IR$Revenu.IR))
  tab_IR$Taux.IR<-as.numeric(as.character(tab_IR$Taux.IR))
  
  for (i in length(tab_IR[,1]):2) {
    imp<-imp+apply(rbind(rep(0,horiz),(QFi-tab_IR[i,1])),2,max)*tab_IR[i,2]
    QFi<-QFi-apply(rbind(rep(0,horiz),(QFi-tab_IR[i,1])),2,max)
  }
  return(imp)
}