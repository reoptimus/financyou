###############################
#
# Fonction des constitution de la table de engagements à honorer
#
# cree le 17/01/2020
# par Sebastion Gallet
#
###############################

# fonction pour generer la carte des engagements à honorer
engagement<-function (sum_cuml) {
  
# definition du tableau des contraintes en montant a t0 bloque sur tout D
tabl_eur_cont<-array(0,dim=c(length(table_invest_t0$ID),length(sum_cuml)))
tabl_eur_cont<-array(rep(t(table_invest_t0$Valeur_t0),length(sum_cuml)),dim=c(length(table_invest_t0$Valeur_t0),length(sum_cuml)))

# contrainte sur tous les placements non liquide
tabl_eur_cont[which(table_invest$Liquide==1),]<-0

# definition du tableau des contraintes en eur pour les r (remboursement d'emprunt)
tabl_eur_cont_r<-array(0,dim=c(dim(GSE_plac_taxes_an)[4]-dim(tabl_eur_cont)[1],dim(tabl_eur_cont)[2])) # nb possible de credits
tabl_eur_cont<-abind(tabl_eur_cont,tabl_eur_cont_r,along=1)
# position des lignes de credits deja prises
pos_crd_to<-which(table_invest_t0$Annuite!=0)+length(table_invest$ID)-length(which(table_invest$annee_empr==0)) # position des credit deja pris

# capital rembourse a t0 sur les credit R
#Cap_remb_t0<-(table_invest_t0$Annuite/table_invest_t0$Taux*((1+table_invest_t0$Taux)^(-(table_invest_t0$An_rest))-(1+table_invest_t0$Taux)^(-(table_invest_t0$An_tot))))

# formule pour un credit a remboursement constant
#################################################
if ( sum(table_invest_t0$Annuite!=0)!=0 ) {
for ( i in 1:length(tabl_eur_cont[1,]) ) { #constitution des triangles de remboursements
  for ( j in 1:length(pos_crd_to)) {
    # calcul de la part de capital dans les remboursements de prets
    if ((i-1)<=table_invest_t0$An_rest[which(table_invest_t0$Annuite!=0)[j]]) { # i toujours en annee
      sum_annuite<-table_invest_t0$Annuite[which(table_invest_t0$Annuite!=0)[j]] *i
      #Cap_remb<-(table_invest_t0$Annuite/table_invest_t0$Taux*((1+table_invest_t0$Taux)^(-(table_invest_t0$An_rest-(i)))-(1+table_invest_t0$Taux)^(-(table_invest_t0$An_tot)))-Cap_remb_t0)[which(table_invest_t0$Annuite!=0)[j]]
    } else {
      sum_annuite<-table_invest_t0$Annuite[which(table_invest_t0$Annuite!=0)[j]] *table_invest_t0$An_rest[which(table_invest_t0$Annuite!=0)[j]] 
      #Cap_remb<-(table_invest_t0$Annuite/table_invest_t0$Taux*(1-(1+table_invest_t0$Taux)^(-(table_invest_t0$An_tot-1))))[which(table_invest_t0$Annuite!=0)[j]]
    }
    tabl_eur_cont[pos_crd_to[j],i]<-sum_annuite #Cap_remb
  }
}
} # fin if sur existance de contraintes
return(tabl_eur_cont)

} #fin de la fonction