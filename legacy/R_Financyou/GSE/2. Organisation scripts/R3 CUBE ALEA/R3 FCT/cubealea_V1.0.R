###############
# fct: Cubealea
###############
#fonction qui genere le cube des variables aleatoire a partir de la matrice de correlation
#
# crée le: 13/10/2017 par Sébastien Gallet
# modifiée le: 13/10/2017 par Sébastien Gallet
#
# Version : 1.0
#
# variables d entree#######################
# nom_in = matrice de corrélation ( j X j )
# nom_com_loc = variable locale TBD
# nom_com_glob = variables globales (n et H)
# nom_out = nom donne a la var de sortie, ici le cube de var aléatoire correlees ( j X n X T )
###########################################

# Fonction pour generation nombre aletoire correle
cubealea <- function(nom_corr_csv,nom_sortie) 
{
  
  # pour le test en local
  NS<-N
  T<-T

  #chargement de la matrice et enregistrement au format RDATA
  matcorr<-read.csv( file= paste("./R3 IN/",nom_corr_csv, sep="") , header=TRUE , sep=";")
  matcorr<-matcorr[,-1] #retrait de la premiere colonne avec les noms
  
  #Factorisation de la Cholesky de la matrice de corrélation (matrice triangulaire inférieure)
  #1 Tx_Inflation	2 Rdt_Immobilier	3 Tx_reel_long	4 Tx_reel_court	5 Rdt_exces_actions
    Mat_Chol=t(chol(matcorr))
  
  #Calcul du nombre d'indice d'actifs dans la matrice de corrélation
  Nbcorr=length(matcorr)
  
  #Simulation matrice de lois N(0,1) à 3 dimensions (nb correlations, nb simulations, nb annees projection)
  Mat_norm=array(rnorm(Nbcorr*NS*T),dim=c(Nbcorr,NS,T))
  
  #Initialisation à 0 de la matrice à 3 dimensions des résidus
  Mat_res=array(0,dim=c(Nbcorr,NS,T))
  
  #Construction de la matrice à 3 dimensions avec les var alea correlees
  for(i in 1:Nbcorr){
    for(n in 1:NS){
      for(k in 1:T){  
        Mat_res[i,n,k]= sum(Mat_Chol[i,]*Mat_norm[,n,k]) 
      }
    }
  }
  
  #savegarde au format Rdata de la mat de residus correles
  save(Mat_res, file=paste("./R3 OUT/",nom_sortie,".Rda",sep=""))
  rm(list=c('Mat_res','Mat_norm','Mat_Chol','Nbcorr','NS','T'))
  gc()
  
}