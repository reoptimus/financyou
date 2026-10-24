########################################
#
# Fonction de recherche de l'optimum Marko/Michaud sous contrainte
#
# les contraintes en % du capital evolue ? chaque pas de temps
# c'est donc une matrice des contraintes mat_constr [dim = Nb_plac X Tp]
# sortie: Moyenne des optimum Markovien pour chaque ann?e et ap?tences (d?finie ici)
# Matrice soltot[dim = Nb_plac X D X tp_D X Nb_Aversion ]
# ATTENTION: pour acceler, on prend le rendement a Tp=1 uniquement
# on considère que les rendements sont identiques dans le temps
#
# Version 4 + chemin shinyapps
# cree le 14/01/2020
# modifiee le 06/02/2020
# par S?basten Gallet
########################################

Boot_Michaud <- function(GSE_plac_taxes,pas_t,Nbboots,Aversion,tabl_cont_t)
  { #debut fonction
  # library(MASS)
  # library(plotly)
  
  # reptravail<-"E:"
  # reptravail<-paste0(reptravail,"/R_Financyou")
  # pas_t<-0.5
  # Nbboots<-50 #nombre de paquets (+ le nb de ligne par paquet est petit et plus il y a de diversit?!)
  # nom_sortie<-"soltot"
  # GSE_plac_taxes<-GSEpp_an # [N,Tp,D,Actifs]
  # tabl_cont_t<-tabl_pourc_cont0

NS= dim(GSE_plac_taxes)[1] # nombre de simulations
D = dim(GSE_plac_taxes)[3] # maturit? des projections en pas de temps!!!
Nb_actifs<-dim(GSE_plac_taxes)[4]
compteur<-1

# choix de l'echantillonnage
Nbligboot<-floor(NS/Nbboots) # Nb de lignes de tirage par paquet

# si on exclu les engagements de l'optimum
# le calcul ne depend plus de TP mais seulement de l'activation a t0
soltot<-array(0,dim=c(Nb_actifs,D)) # vecteur opti Marko

  contraintes<-tabl_cont_t[] #vecteur en % des placements

for (tp_D in 1:D) { # boucle sur la duree du placement: on ne calcul que sur le triangle pour accelerer

#pour un echantillon
solboot<-array(0, dim=c(Nbboots,Nb_actifs)) #dim=c(Nbboots*2,Nb_actifs)

  for (Numboots in 1:Nbboots) {
    #####################
    # ATTENTION: pour acceler, on prend le rendement a Tp=1 uniquement
    # on considère que les rendements sont identiques dans le temps
    #####################
     MatE<-GSE_plac_taxes[(Nbligboot*(Numboots-1)+1):(Nbligboot*Numboots),1,tp_D,1:Nb_actifs]
     Esp<-apply(MatE,2,mean) # la moyenne sur les diff?rents paquets
     Cov<-cov(MatE)
  
  #Optimisation Markovitz
  #avec contraintes
  
    #contrainte: somme = 100%
    MatMarkCov<-array(1,dim=c((Nb_actifs+1),(Nb_actifs+1)))
    MatMarkCov[Nb_actifs+1,Nb_actifs+1]<-0
    MatMarkCov[1:Nb_actifs,1:Nb_actifs]<-Cov
  
    MatMarkE<-array(0,dim=c((Nb_actifs+1),1))
    MatMarkE[1:Nb_actifs,1]<-t(Esp)
    
    Vcont<-array(0,dim=c((Nb_actifs+1),1))
    Vcont[(Nb_actifs+1),1]<-1
    
    # ajout des contraintes
    for (i in 1:Nb_actifs) {
      if ( (contraintes[i]!=0) ) {
        MatMarkCov2<-array(0,dim=c((length(MatMarkCov[,1])+1),(length(MatMarkCov[,1])+1)))
        MatMarkCov2[1:length(MatMarkCov[,1]),1:length(MatMarkCov[,1])]<-MatMarkCov
        MatMarkCov2[length(MatMarkCov2[,1]),i]<-1
        MatMarkCov2[i,length(MatMarkCov2[,1])]<-1
        MatMarkCov<-MatMarkCov2
        
        MatMarkE2<-array(0,dim=c(length(MatMarkCov[,1]),1))
        MatMarkE2[1:length(MatMarkE),1]<-MatMarkE
        MatMarkE<-MatMarkE2
        
        Vcont2<-array(0,dim=c(length(MatMarkE),1))
        Vcont2[1:length(Vcont),1]<-Vcont
        Vcont2[length(MatMarkE),1]<-contraintes[i] #contrainte peut etre >0 mais toujours <1
        Vcont<-Vcont2
        
        compteur<-compteur+1
      } # fin du if
    } # fin de boucle pour marquer les contraintes
        
        #recalcul du l'optimum Markovien
        MatMarkCovInv<-ginv(MatMarkCov, tol = sqrt(.Machine$double.eps)) #solve(MatMarkCov)
        sol1<-MatMarkCovInv %*% MatMarkE
        sol2<-MatMarkCovInv %*% Vcont
        sol<-(1/Aversion)*sol1+sol2
 
  #marquage des contraintes saturees a t
        satur<-array(0,dim=c(Nb_actifs,1)) # aucune contrainte
        satur[which(tabl_cont_t[]!=0)]<-1
        
  for (iter in 1:Nb_actifs) { # on refait a chaque fois pour chaque nouvelles contraintes saturees
    
  #contrainte de non vente a decouvert sol(i)>0 et respect de la contrainte t0 (sans possiblite de remboursement anticipe)
  for (i in 1:Nb_actifs) {
    if ( (satur[i]==0) && (sol[i]<0) ) {
      satur[i]<-1
    MatMarkCov2<-array(0,dim=c((length(MatMarkCov[,1])+1),(length(MatMarkCov[,1])+1)))
    MatMarkCov2[1:length(MatMarkCov[,1]),1:length(MatMarkCov[,1])]<-MatMarkCov
    MatMarkCov2[length(MatMarkCov2[,1]),i]<-1
    MatMarkCov2[i,length(MatMarkCov2[,1])]<-1
    MatMarkCov<-MatMarkCov2
    
    MatMarkE2<-array(0,dim=c(length(MatMarkCov[,1]),1))
    MatMarkE2[1:length(MatMarkE),1]<-MatMarkE
    MatMarkE<-MatMarkE2
    
    Vcont2<-array(0,dim=c(length(MatMarkE),1))
    Vcont2[1:length(Vcont),1]<-Vcont
    Vcont2[length(MatMarkE),1]<-0 #contrainte peut etre >0 mais toujours <1
    Vcont<-Vcont2
    
    #recalcul du l'optimum Markovien
    MatMarkCovInv<-ginv(MatMarkCov, tol = sqrt(.Machine$double.eps)) #solve(MatMarkCov)
    sol1<-MatMarkCovInv %*% MatMarkE
    sol2<-MatMarkCovInv %*% Vcont
    sol<-(1/Aversion)*sol1+sol2
    
    compteur<-compteur+1
    } # fin boucle if
  } # fin boucle
  } # fin boucle Iter
  sol<-sol[1:Nb_actifs]
  
  #mise en forme des solutions des differents bootstraps
  solboot[Numboots,]<-sol
  } # fin de la boucle bootstrap
######################
#calcul de la moyenne des solutions
sol<-t(apply(solboot, 2,mean))
sol<-sol/sum(sol)

#Ventilation optimum Markovienne moyenne par duree en pas_t et apetence
soltot[,tp_D]<-t(sol)
}

return(soltot)
gc()

} #fin de la function
