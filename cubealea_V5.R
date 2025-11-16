###############
# fct: Cubealea
###############
#fonction qui genere le cube des variables aleatoire a partir de la matrice de correlation
#
# crée le: 13/10/2017 par Sébastien Gallet
# modifiée le: 02/01/2019 par Sébastien Gallet
#
# Version : 4.0 (utilise les residus Rt exterieur et accelère le calcul)
#
# variables d entree#######################
# Rt_norm = matrice des residus de Rt
# nom_corr_csv = nom du fichier comportant la matrice de correlation des résidus
# nom_sortie = nom a donner a la variable cube des nombres aléatoires corrélés
# pas = pas de temps du GSE
###########################################

# Fonction pour generation nombre aletoire correle
cubealea <- function(Rt_norm,N,H,nom_corr_csv,nom_sortie,pas) 
{
  library(abind) #equivalent cbind pour array() de dim >2
  library(xlsx)
  # N=1000
  # H=60
  # nom_corr_csv="Corr_ResidAhlgrim_V2.xlsx"
  # nom_sortie="Epsilon.Rda"
  # pas=0.5
  # Rt_norm=Mat_resid_Rt
  # reptravail<-"//intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG_V2/2. Organisation scripts/"
  # setwd(reptravail)
  
  # taille des variables
  NS<-N/2
  Tf<-H/pas

  #chargement de la matrice et enregistrement au format RDATA
  matcorr<-read.xlsx(paste0(reptravail,"/R3 CUBE ALEA/R3 IN/",nom_corr_csv), sheetIndex = 1)
  
  matcorr<-matcorr[,-1] #retrait de la premiere colonne avec les noms
  matcorr<-cbind(matcorr[,4],matcorr[,-4])
  matcorr<-rbind(matcorr[4,],matcorr[-4,])
  
  #Factorisation de la Cholesky de la matrice de corrélation (matrice triangulaire inférieure)
  #1 Tx_Inflation	2 Rdt_Immobilier	3 Tx_reel_long	4 Tx_reel_court	5 Rdt_exces_actions
  # reclassé en 
  #1 Tx_reel_court 2 Tx_Inflation	3 Rdt_Immobilier	4 Tx_reel_long	5 Rdt_exces_actions
  
  Mat_Chol=t(chol(matcorr))
  
  #Calcul du nombre d'indice d'actifs dans la matrice de corrélation
  Nbcorr=length(matcorr)
  
  #Simulation matrice de lois N(0,1) à 3 dimensions (nb correlations, nb simulations, nb annees projection)
  Mat_norm<-array(rnorm((Nbcorr-1)*NS*Tf),dim=c((Nbcorr-1),NS,Tf))
  Mat_norm<-abind(Mat_norm,-Mat_norm, along = 2) #ajout des tirages antithétique
  Mat_norm<-abind(Rt_norm,Mat_norm,along=1) #on reprend Rt_norm

  #Initialisation à 0 de la matrice à 3 dimensions des résidus
  Mat_res=array(0,dim=c(Nbcorr,NS*2,Tf))
  
  #Construction de la matrice à 3 dimensions avec les var alea correlees
  for(i in 1:Nbcorr){
      for(k in 1:Tf){  
        Mat_res[i,,k]= apply((Mat_Chol[i,]*Mat_norm[,,k]),2,sum)
      }
  }

  
  #remise dans l'ordre des actifs
  Mat_res<-Mat_res[c(2,3,4,1,5,6),,]
  
  #savegarde au format Rdata de la mat de residus correles
  save(Mat_res, file=paste(reptravail,"/R2 CUBE/R2 IN/",nom_sortie,sep=""))
  rm(list=c('Mat_res','Mat_norm','Mat_Chol','Nbcorr','NS','Tf','H','pas'))
  gc()
  
}