# Financyou
# definition des projets de l'utilisateur
# donn?es d'entree: 
# - matrice type impact X 5 var(AnDebut, Mdebut, Mvers, duree, Msortie)
# - horizon_placement
# donn?es sortie: matrice var impactee X horizon_placement

Exp_fin<- function (horiz,AnDebut, Mdebut, Mvers, duree, Msortie,pente) {
  pas_t<-1
  # horiz<-20
  # pas_t<-1
  # AnDebut<-as.Date("2035-04-27")
  # Mdebut<-0
  # Mvers<-208000
  # duree<-3
  # Msortie<-0
  # pente<-0
  #changement d'unite en pas_t

  AnDebut<-floor(as.numeric(difftime(AnDebut, format(Sys.Date(), "%Y-%m-%d") , units = "days"),units="days")/(pas_t*365))
  duree<-min( horiz-AnDebut , ceiling(duree/pas_t) )
  M_projets<-c(AnDebut, Mdebut, Mvers, duree, Msortie,pente)
  
  Hist_detail<-array(0,dim=c(1,horiz+1))
    if (M_projets[1]>=0) {
    #ecriture du premier versement du projet
      Hist_detail[1,M_projets[1]+1]<-M_projets[2]
      #ecriture de la sequence de versement
      if (M_projets[4]>0) {
      Hist_detail[1,((M_projets[1]+2):(M_projets[1]+1+M_projets[4]))]<-rep(M_projets[3],M_projets[4])
      Hist_detail[1,(M_projets[1]+1+M_projets[4])]<-Hist_detail[1,(M_projets[1]+1+M_projets[4])]+M_projets[5] #ajout du montant de sortie (ex:revente>montant negatif)
      }
    } else {
      M_projets[1]<-0
      Hist_detail[1,M_projets[1]+1]<-M_projets[2]
      #ecriture de la sequence de versement
      if (M_projets[4]>0) {
        Hist_detail[1,((M_projets[1]+2):(M_projets[1]+1+M_projets[4]))]<-rep(M_projets[3],M_projets[4])
        Hist_detail[1,(M_projets[1]+1+M_projets[4])]<-Hist_detail[1,(M_projets[1]+1+M_projets[4])]+M_projets[5] #ajout du montant de sortie (ex:revente>montant negatif)
    }
    }
  return(Hist_detail)
}
