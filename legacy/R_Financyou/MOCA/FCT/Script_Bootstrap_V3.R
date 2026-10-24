########################################
#
# Fonction de recherche de l'optimum Marko/Michaud sous contrainte
#
# les contraintes en % du capital evolue à chaque pas de temps
# c'est donc une matrice des contraintes mat_constr [dim = Nb_plac X Tp]
# sortie: Moyenne des optimum Markovien pour chaque ann?e et ap?tences (d?finie ici)
# Matrice soltot[dim = Nb_plac X D X tp_D X Nb_Aversion ]
#
# Version 3
# cree le 14/01/2020
# modifiee le 17/01/2020
# par Sébasten Gallet
########################################


Boot_Michaud <- function(reptravail,GSE_plac_taxes,pas_t,Nbboots,Aversion,nom_sortie,tabl_cont_t)
  { #debut fonction
  library(MASS)
  library(plotly)
  
  # reptravail<-"E:"
  # reptravail<-paste0(reptravail,"/R_Financyou")
  # pas_t<-0.5
  # Nbboots<-50 #nombre de paquets (+ le nb de ligne par paquet est petit et plus il y a de diversité!)
  # nom_sortie<-"soltot"
  # GSE_plac_taxes<-GSEpp # [N,Tp,D,Actifs]
  tabl_cont_t<-tabl_pourc_cont

NS= dim(GSE_plac_taxes)[1] # nombre de simulations
D = dim(GSE_plac_taxes)[3] # maturit? des projections en pas de temps!!!
Tp <- D # indice de la date à laquelle est optimise l'invest
Nb_actifs<-dim(GSE_plac_taxes)[4]
compteur<-1

# choix de l'echantillonnage
Nbligboot<-floor(NS/Nbboots) # Nb de lignes de tirage par paquet

#formation des sousmatrices + calcul de l'esp?rance + Variance + Covar
#pour une ann?e T=t, Aversion,
#Aversion<-c(0.1,1,10,100,1000)

soltot<-array(0,dim=c(Nb_actifs,D,Tp,length(Aversion))) # vecteur opti Marko
# Numboots=1
# tp_D=2
# Ap=2
# D=1
# i=10

for ( tp_T in 1:Tp) { # boucle sur la date à laquelle est vu le placement
  
  contraintes<-tabl_cont_t[,tp_T] #vecteur en % des placements

for (tp_D in 1:(D-tp_T+1)) { # boucle sur la duree du placement: on ne calcul que sur le triangle pour accelerer

 for (Ap in 1:length(Aversion)){

#pour un ?chantillon
solboot<-array(0, dim=c(Nbboots,Nb_actifs)) #dim=c(Nbboots*2,Nb_actifs)

#boucle sur les echantillons bootstrap?s

#for (j in 1:2) { # boucle alea vs ordonne

  for (Numboots in 1:Nbboots) {
    # changement de methode 1 fois sur 2 pour le tirage du bootstrap
      # if (j==2) { # methode aleatoire
      #   MatE<-GSE_plac_taxes[runif(Nbboots,1,NS),1,tp_D,1:Nb_actifs] #ATTENTION, on considère les rendements au temps=1!!
      # }
      # if (j==1) { #methode ordonnee, on utilise 1 seul fois un tirage
         MatE<-GSE_plac_taxes[(Nbligboot*(Numboots-1)+1):(Nbligboot*Numboots),1,tp_D,1:Nb_actifs] #ATTENTION, on considère les rendements au temps=1!!!!
      # }
  
  Esp<-apply(MatE,2,mean) # la moyenne sur les différents paquets
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
        sol<-(1/Aversion[Ap])*sol1+sol2
 
  #marquage des contraintes saturees
  satur<-apply(MatMarkCov[1:Nb_actifs,(Nb_actifs+2):length(MatMarkCov[1,])],1,sum)

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
    sol<-(1/Aversion[Ap])*sol1+sol2
    
    compteur<-compteur+1
    } # fin boucle if
  } # fin boucle
  } # fin boucle Iter
  sol<-sol[1:Nb_actifs]
  
  #mise en forme des solutions des diff?rents bootstraps
  solboot[Numboots,]<-sol
  #solboot[Numboots+(j-1)*Nbboots,]<-sol # solution avec bootstrp aleatoire
  } # fin de la boucle bootstrap
# } # fin de la boucle sur j type de tirage bootstrap (alea vs ordonne)
######################
#calcul de la moyenne des solutions
sol<-t(apply(solboot, 2,mean))
sol<-sol/sum(sol)

#Ventilation optimum Markovienne moyenne par duree en pas_t et apetence
soltot[,tp_D,tp_T,Ap]<-t(sol)
}}}

# elimination des trops petites parts
# soltot[which(abs(soltot)<1e-5,arr.ind = TRUE)]<-0
# # renormalisation
# soltot<-soltot/aperm(array(rep(apply(soltot,c(2,3),sum),dim(soltot)[1]),dim=c(dim(soltot)[2],dim(soltot)[3],dim(soltot)[1])),c(3,1,2))
# dim(soltot)

save(soltot,file=paste0(reptravail,"/MOCA/IN/",nom_sortie,".Rda"))
return(compteur)

#efface les donnees superflues
rm(list=ls(all=TRUE))
gc()

} #fin de la function
