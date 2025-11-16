###############
# fct: Inflation
###############
#fonction qui genere l'inflation (option:à partir des taux sans risques cumulés)
#
#
# crée le: 01/12/2018 par Sébastien Gallet
# modifiée le: 
#
# Version : 1
#
# variables d entree#######################
# Tr-Rt.Rda = Matrice N*T des taux sans risques
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
# pas_t = le pas de temps de discretisation du GSE en année
###########################################

Inflation <- function(TrSR,nom_sortie,pas_t,reptravail)
  { #debut fonction

# données annuelle de l'inflation (peut-être plus complexe)
  
  Taux_infl<-0.02
  
# Chargement de la matrice des taux sans risque TrSR : nom Rt
load(paste(reptravail,"/R1 MEFCUBE/R1 IN/",TrSR, sep="") )
#definition de la taille des matrices
try(Rt<-Rt_PMR, silent=TRUE) #fonctionne aussi bien pour RN ou PMR
N<-dim(Rt) [1]
Tf<-dim(Rt) [2]

##################################
# Formation de la matrice de l'inflation
########################

Inflation<-array(0,dim=c(N,Tf))

for (i in 1:(Tf-1)) {
  #if (round(i*pas_t)==(i*pas_t)) {
    Inflation[,i+1]<-log(1+Taux_infl)*pas_t #conversion du taux annuel en continu puis reduction au pas_t
  #}
}

print("Fin de calcul de la tranche Inflation")
flush.console()
  
#savegarde au format Rdata de la matrice des déflateurs
save(Inflation, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie,".Rda",sep=""))

print("Sauvegarde de la tranche Inflation ds /R1 MEFCUBE/R1 IN/")
flush.console()

rm(list=c('Inflation','N','Tf'))
#rm(list=ls())
gc()

} #fin fonction