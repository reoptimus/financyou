#Chargement des données
setwd(CalibrageDonnees)

Tx_Inflation<-scan("Tx_Inflation.txt")
Rdt_Immobilier<-scan("Rdt_Immobilier.txt")
Tx_reel_long<-scan("Tx_reel_long.txt")
Tx_reel_court<-scan("Tx_reel_court.txt")
Rdt_exces_actions<-scan("Rdt_exces_actions.txt")

#Définition du nombre d'observation dans le fichier en entrée
Nobs<-length(Tx_Inflation)
#Définition des séries
Tx_Inflation_tplusun=Tx_Inflation[2:Nobs]
Tx_Inflation_t=Tx_Inflation[1:(Nobs-1)]
Rdt_Immobilier_tplusun=Rdt_Immobilier[2:Nobs]
Rdt_Immobilier_t=Rdt_Immobilier[1:(Nobs-1)]
Tx_reel_long_tplusun=Tx_reel_long[2:Nobs]
Tx_reel_long_t=Tx_reel_long[1:(Nobs-1)]
Tx_reel_court_t=Tx_reel_court[1:(Nobs-1)]
Tx_reel_court_tplusun=Tx_reel_court[2:Nobs]

#Régression par les MCO
reg_Tx_Inflation=lm(Tx_Inflation_tplusun~Tx_Inflation_t)
reg_Rdt_Immobilier=lm(Rdt_Immobilier_tplusun~Rdt_Immobilier_t)
reg_Tx_reel_long=lm(Tx_reel_long_tplusun~Tx_reel_long_t)

#Calcul de la différence entre les taux de LT estimés et les taux de CT observés et ajustement de la taille du vecteur
Chap_Tx_reel_long_tplusun=coef(reg_Tx_reel_long)[1]+coef(reg_Tx_reel_long)[2]*Tx_reel_long_t
Diff_ChapLT_CT=Chap_Tx_reel_long_tplusun-Tx_reel_court_tplusun
Diff_ChapLT_CT=Diff_ChapLT_CT[1:(Nobs-2)]
#Calcul de la différence entre les taux de CT observés en t+1 et ceux observés en t
Diff_CT=Tx_reel_court_tplusun-Tx_reel_court_t
Diff_CT=Diff_CT[2:(Nobs-1)]
#Régression par les MCO (suite)
reg_DiffTx_reel_court=lm(Diff_CT~Diff_ChapLT_CT-1)

#Détermination des résidus
Resid_Tx_Inflation=resid(reg_Tx_Inflation)/(sd(resid(reg_Tx_Inflation))*sqrt((Nobs-2)/(Nobs-3)))
Resid_Tx_Inflation=Resid_Tx_Inflation[2:(Nobs-1)]
Resid_Rdt_Immobilier=resid(reg_Rdt_Immobilier)/(sd(resid(reg_Rdt_Immobilier))*sqrt((Nobs-2)/(Nobs-3)))
Resid_Rdt_Immobilier=Resid_Rdt_Immobilier[2:(Nobs-1)]
Resid_Tx_reel_long=resid(reg_Tx_reel_long)/(sd(resid(reg_Tx_reel_long))*sqrt((Nobs-2)/(Nobs-3)))
Resid_Tx_reel_long=Resid_Tx_reel_long[2:(Nobs-1)]
Resid_Tx_reel_court=resid(reg_DiffTx_reel_court)/(sd(resid(reg_DiffTx_reel_court))*sqrt(((Nobs-1)-2)/((Nobs-1)-3)))
Resid_Rdt_exces_actions=(Rdt_exces_actions-(mean(Rdt_exces_actions)-(sd(Rdt_exces_actions)^2)/2))/(sd(Rdt_exces_actions)*sqrt(((Nobs+1)-2)/((Nobs+1)-3)))
Resid_Rdt_exces_actions=Resid_Rdt_exces_actions[3:(Nobs)]

#Rangement des résidus dans un tableau
Tableau_ResidAhlgrim=data.frame(Resid_Tx_Inflation,Resid_Rdt_Immobilier,Resid_Tx_reel_long,Resid_Tx_reel_court,Resid_Rdt_exces_actions)

#Calcul de la matrice de corrélation
Corr_ResidAhlgrim=cor(Tableau_ResidAhlgrim)
#write.csv2(Corr_ResidAhlgrim, file = "Corr_ResidAhlgrim.csv")
##PARTIE 2 : Projection des résidus en tenant compte des corrélations

#Factorisation de la Cholesky de la matrice de corrélation (matrice triangulaire inférieure)
Mat_Chol=t(chol(Corr_ResidAhlgrim))
#Calcul du nombre d'indice d'actifs dans la matrice de corrélation
Nbcorr=sqrt(length(Corr_ResidAhlgrim))
#Simulation matrice de lois N(0,1) à 3 dimensions (nb correlations, nb simulations, nb annees projection)
Mat_norm=array(rnorm(Nbcorr*NS*T),dim=c(Nbcorr,NS,T))
#Initialisation à 0 de la matrice à 3 dimensions des résidus
Mat_res=array(0,dim=c(Nbcorr,NS,T),dimnames = list(c("Inflation","Immobilier", "Tx_long","Tx_court","Exces_actions"),1:NS,1:T))
#Construction de la matrice à 3 dimensions avec les résidus projetés
for(i in 1:Nbcorr){
  for(n in 1:NS){
    for(k in 1:T){  
      Mat_res[i,n,k]= sum(Mat_Chol[i,]*Mat_norm[,n,k]) 
    }
  }
}

#Backtesting sur la matrice de corrélation
#############
#Corr_Mat_res=array(0,dim=c(NS,Nbcorr,Nbcorr))
#for(n in 1:NS){Corr_Mat_res[n,,]=cor(t(Mat_res[,n,1:T])) }

#Test_corr_Mat_res=array(0,dim=c(Nbcorr,Nbcorr),dimnames = list(c("Inflation", "Immobilier", "Tx_long","Tx_court","Exces_actions"),c("Inflation", "Immobilier","Tx_long","Tx_court","Exces_actions")))
#Test_corr_Mat_res[,]=apply(Corr_Mat_res,c(2,3),mean)
