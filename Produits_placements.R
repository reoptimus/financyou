############################
#
# Produits_placements
#
# mise en forme du GSE en GSE de placements reels
# V1 : le 15/05/2019
# S.G.
############################

produits_placements<-function (reptravail,nom_cube,pas_t) {
  
library("xlsx")

# exemple des variables
# reptravail<-paste0("D:/","R_Financyou")
# nom_cube<-"Test_Hist_20200717.Rda"
# pas_t<-0.5 # pas de temps de la diffusion du cube
#############

#############
# chargement du cube GSE
ad_GSE<-"/GSE/2. Organisation scripts/R1 MEFCUBE/R1 OUT/"
#load(paste0(reptravail,ad_GSE,"YE16.Rda"))
load(paste0(reptravail,ad_GSE,nom_cube))
reptravail<-paste0(reptravail,"/GSE+")
# dim(cube)


##################################
# variable interne pour la constitution des produits financiers
matur<-10
extra=0#0.008 # supplement de Rdt pour Ass. Vie vs. OAT10
limit_default<-log(1+0.3) #limite de rendement sur l'annee avant defaut
ab_default<-log(1-0.3) #perte en % du prix sur le rendement annuel
RecoBond<-0.6
RecoCBond<-0.4
#################################

list_actifs<-c("Monetaire",
               "Prix Actions",
               "div actions",
               "Prix + div actions",
               "Prix Immobilier",
               "Loyers immo",
               "Prix + Loyers immo",
               "obligations souveraines AA",
               "obligations souveraines A",
               "obligations souveraines BBB",
               "obligations corpo AA",
               "obligations corpo A",
               "obligations corpos BBB",
               "assurance vie EUR",
               "assurance vie EUR_V2",
               "assurance vie UC")
Nb_actifs<-length(list_actifs)
#taille du cube charg?
nb_TR_ZC<-dim(cube)[3]-8
N<-dim(cube)[1]
TP<-dim(cube)[2]
# d?finition du cube_placement
cube_placement<-array(0,dim=c(N,TP,Nb_actifs))

#chargement de la fonction RdtCumul
source(file=paste0(reptravail,"/R2 CUBE+/R2 Fonctions locale/","F_Rdtcumul.R"))

numero<-1
# Mon?taire : tranche 1
source(file=paste0(reptravail,"/R2 CUBE+/R2 FCT/","Oblig_V1.R"))
Oblig(1,"Monetaire",pas_t,reptravail,limit_default,ab_default,cube)
load(file=paste0(reptravail,"/R2 CUBE+/R2 OUT/","Monetaire","1",".Rda"))
cube_placement[,,numero]<-Rdt_OAT #Rdtcumul(cube[,,nb_TR_ZC+6])*pas_t #a verifier!!! #rendement mon?taire = inflation
numero<-numero+1

# # inflation - Tr 46
# cube_placement[,,numero]<-Rdtcumul(cube[,,nb_TR_ZC+6])*pas_t #a verifier!!!
# numero<-numero+1

# Prix Actions : tranche 42 pour Eq capital change
cube_placement[,,numero]<-Rdtcumul(cube[,,nb_TR_ZC+2])
numActPrix<-numero
numero<-numero+1

# Dividende Actions : tranche 43 pour Eq div return
cube_placement[,,numero]<-Rdtcumul(cube[,,nb_TR_ZC+3])
numActDiv<-numero
numero<-numero+1

# Prix + Dividende Actions : tranche 43 pour Eq div return
cube_placement[,,numero]<-Rdtcumul(cube[,,nb_TR_ZC+7])
numActTot<-numero
numero<-numero+1

# Prix Immobilier 
cube_placement[,,numero]<-Rdtcumul(cube[,,nb_TR_ZC+4])
numImmPrix<-numero
numero<-numero+1

# Loyers Immobilier : tranche 48 pour Prop tot return
cube_placement[,,numero]<-Rdtcumul(cube[,,nb_TR_ZC+5])
numImmLoy<-numero
numero<-numero+1

# Prix + Loyers Immobilier : tranche 48 pour Prop tot return
cube_placement[,,numero]<-Rdtcumul(cube[,,nb_TR_ZC+8])
numImmTot<-numero
numero<-numero+1

# 7- obligations

# chargement de la fonction obligation et calcul le rendement 
# d'une oblig(matur) sans risque-> enregistrement ds
nom_sortie_OAT<-"Tr-OAT"

Oblig(matur,nom_sortie_OAT,pas_t,reptravail,limit_default,ab_default,cube)
# chargement de la tranche des rendement sans risque d'une obligation(matur)
load(file=paste0(reptravail,"/R2 CUBE+/R2 OUT/",nom_sortie_OAT,matur,".Rda"))


#calcul des saut de rendement suite ? changement de notation
source(file=paste0(reptravail,"/R2 CUBE+/R2 FCT/","Oblig_credit_spread_V1.R"))
Oblig_spread(matur,cube,pas_t,reptravail,RecoBond,RecoCBond)
# chargement du cube des spread de rendements/grade souverain
load(file=paste0(reptravail,"/R2 CUBE+/R2 OUT/","cube_rdt_grade.Rda"))

# souverain AA
cube_placement[,,numero]<-Rdtcumul(Rdt_OAT+cube_rdt_grade[,,2])
numAA<-numero
numero<-numero+1
# souverain A
cube_placement[,,numero]<-Rdtcumul(Rdt_OAT+cube_rdt_grade[,,3])
numA<-numero
numero<-numero+1
# souverain BBB
cube_placement[,,numero]<-Rdtcumul(Rdt_OAT+cube_rdt_grade[,,4])
numBBB<-numero
numero<-numero+1
rm(cube_rdt_grade)
gc()

# 10- obligations corporates
# chargement du cube des spread de rendements/grade souverain
load(file=paste0(reptravail,"/R2 CUBE+/R2 OUT/","cube_rdt_gradeC.Rda"))
# corporates AA
cube_placement[,,numero]<-Rdtcumul(Rdt_OAT+cube_rdt_gradeC[,,2])
numAA_C<-numero
numero<-numero+1
# corporates A
cube_placement[,,numero]<-Rdtcumul(Rdt_OAT+cube_rdt_gradeC[,,3])
numA_C<-numero
numero<-numero+1
# corporates BBB
cube_placement[,,numero]<-Rdtcumul(Rdt_OAT+cube_rdt_gradeC[,,4])
numBBB_C<-numero
numero<-numero+1
rm(cube_rdt_gradeC)
gc()

# 13- assurance vie Eur methode 1 EUR : ici oblig avec un extra rdt
#calcul du rendement cumul? pour l'assurance vie equivalente ? 
# moyenne OAT10 sur 5 ans+ extra%
#Rdt_AssVieEur<-mapply(max,Rdtcumul(cube_placement[,,7],gl=5,"Y")/5,cube_placement[,,7]) # modele sur historique
Rdt_AssVieEur<-mapply(max,0.9*(cube_placement[,,7]+extra*pas_t),0.00) # autre solution de model: reglementaire
cube_placement[,,numero]<-Rdt_AssVieEur
numero<-numero+1

# assurance vie Eur methode 2 (voir fichier XL de repartition)
# repartition par nature , frais ? 5% (mois de frais que sur les UC)
pOb_AA<-0.082*0.329
pOb_A<-0.704*0.329
pOb_BBB<-0.214*0.329
pObC_AA<-0.082*0.504
pObC_A<-0.704*0.504
pObC_BBB<-0.214*0.504
pAct<-0.123
pImm<-0.044
cube_placement[,,numero]<-0.90*(pAct*(cube_placement[,,numActPrix]+cube_placement[,,numActDiv])+
                                 pImm*(cube_placement[,,numImmTot]+cube_placement[,,numImmLoy])+
                                 pOb_AA*cube_placement[,,numAA]+
                                 pOb_A*cube_placement[,,numA]+
                                 pOb_BBB*cube_placement[,,numBBB]+
                                 pObC_AA*cube_placement[,,numAA_C]+
                                 pObC_A*cube_placement[,,numA_C]+
                                 pObC_BBB*cube_placement[,,numBBB_C])
cube_placement[,,numero]<-mapply(max,cube_placement[,,numero],cube_placement[,,(numero-1)])
numero<-numero+1

# assurance vie UC (voir fichier XL de repartition)
# frais ? 10% (plus de frais sur les UC)
pOb_AA<-0.082*0.095
pOb_A<-0.704*0.095
pOb_BBB<-0.214*0.095
pObC_AA<-0.082*0.405
pObC_A<-0.704*0.405
pObC_BBB<-0.214*0.405
pAct<-0.486
pImm<-0.014
#pOb_AAA+pOb_AA+pOb_BB+pObC_AAA+pObC_AA+pObC_BB+pAct+pImm
cube_placement[,,numero]<-(pAct*(cube_placement[,,numActPrix]+cube_placement[,,numActDiv])+
                             pImm*(cube_placement[,,numImmPrix]+cube_placement[,,numImmLoy])+
                             pOb_AA*cube_placement[,,numAA]+
                             pOb_A*cube_placement[,,numA]+
                             pOb_BBB*cube_placement[,,numBBB]+
                             pObC_AA*cube_placement[,,numAA_C]+
                             pObC_A*cube_placement[,,numA_C]+
                             pObC_BBB*cube_placement[,,numBBB_C])
numero<-numero+1

###########################################################################
### On sauvegarde exp(somme(R))!!!! les rendements cumul?s sur la p?riode!!!
cube_placement<-exp(cube_placement)
###########################################################################

# save du cube GSE_produits_placements
save(cube_placement,list_actifs,list_actifs,file=paste0(reptravail,"/R2 CUBE+/R2 OUT/","GSE+.Rda"))

rm(list=ls())
gc()

} #fin de la fonction

