# yaali
# definition des projets de l'utilisateur
# données d'entree: 
# - matrice nb_projet X 5 var(AnDebut, Mdebut, Mvers, duree, Msortie)
# - horizon_placement
# - revenue salarié Net
# données sortie: matrice nb_projet X horizon_placement

Exp_fin<- function (M_projets,horiz,salNet,epar) {
  # retrait des noms des projets
  M_projets<-M_projets[,2:length(M_projets[1,])]
  
#calcul des annuités et ecriture de l historique
  nb_proj<-dim(M_projets)[1]
  Hist_detail<-array(0,dim=c(nb_proj+1,horiz+1))
  
  for (i in 1:nb_proj){
    if (M_projets[i,1]!=0) {
    #ecriture du premier versement du projet
      Hist_detail[i,M_projets[i,1]+1]<-M_projets[i,2]
      #ecriture de la sequence de versement
      if (M_projets[i,4]>0) {
      Hist_detail[i,((M_projets[i,1]+2):(M_projets[i,1]+1+M_projets[i,4]))]<-rep(M_projets[i,3],M_projets[i,4])
      Hist_detail[i,(M_projets[i,1]+1+M_projets[i,4])]<-M_projets[i,5] #ajout du montant dde sortie (ex:revente>montant negatif)
      }
    }
  }
  plot(apply(Hist_detail,2,sum),type='o')
  
  #ajout de l'épargne et des salaires
  Hist_detail[nb_proj+1,1]<--epar
  Hist_detail[nb_proj+1,(2:(horiz+1))]<-rep(-salNet,(horiz))
  
  #calcul de la somme cumulee
  sum_cuml<-apply(Hist_detail,2,sum)
  for (i in 1:horiz){
    sum_cuml[i+1]<-sum_cuml[i]+sum_cuml[i+1]
  }
  sum_cuml<--sum_cuml
  #sum_cuml<-approx(1:length(sum_cuml), sum_cuml, xout = seq(1,length(sum_cuml),0.5), method="linear", ties="ordered")$y
  length(sum_cuml)
  plot(sum_cuml,type='l')
  return(sum_cuml)
}