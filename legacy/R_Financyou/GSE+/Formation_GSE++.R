########################
#
# Fichier de création GSE++ à partir de GSE
#
########################

formation_GSEpp<-function(reptravail,Investmoy,Tr_imp,D,pas_t,numerotation){
  
# reptravail<-paste0("D:/","R_Financyou")
# pas_t<-0.5 # pas de temps de la diffusion du cube
# D<-30 #(Tp-1) #duree de l'investissement
# Investmoy<-200000 #investissement moyen retenue
# Net_imposable<-80000
# numerotation<-"20200114"

#### Formation du GSE+: produit du mache ####
source(file=paste0(reptravail,"/GSE+/R2 CUBE+/R2 FCT/Produits_placements.R"))

# variables
nom_cube<-"Test_Hist_20200114.Rda"

# fonction
produits_placements(reptravail,nom_cube,pas_t)
############

#### Formation du GSE++: rendement avec taxes et impots ####
source(file=paste0(reptravail,"/GSE+/R1 CUBE++/R1 FCT/Earn_Aft_Int_TaxesV2.R"))

# variables
table_placement<-"Table_placements"
cubecumul<-"GSE+.Rda" #Test_ReO.V1.Rda"
titre<-paste0("cas ",numerotation,":invest ",Investmoy/1000,"kEur, Tr_imp ",Tr_imp,"pourc")
reptravail<-"D:"
reptravail<-paste0(reptravail,"/R_Financyou")

# fonction
Earn_Aft_Int_Taxes(cubecumul,pas_t,D,reptravail,table_placement,Investmoy,Tr_imp,numerotation)
############
}