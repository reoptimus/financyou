#Earning after interests and taxes
#fonction qui prend le cube GSE en entr?e et qui donne le cube GSE_pls&taxes en sorite
# D est la dur?e de l'investissement
# hyp: l'esp?rance des rendements pour une dur?e d'investissement n'?volue pas au cour du temps
###################################
# Modifi?e le 28/05/2020
#
# Entree: Cube nom du fichier Rda du GSE
#         reptravail chemin du fichier de travail
# sortie: GSE++ propre au client
#
# Modification : cube hors loyer (contés au niveau du flux certain). Uniquement flux et impots de sorti
# Modification 2 : decoupage du GSE pour permettre l' assemblage linéaire d un GSE propre a chaque client

Earn_Aft_Int_Taxes<-function(hist_,tab_chrono) {
  
#donnee entree type
  pas_t<-0.5 # pas du GSE
  cubecumul<-"GSE+.Rda" #Test_ReO.V1.Rda"
  numerotation<-"20200114"
  reptravail<-"D:"
  D<-20 #(Tp-1) #duree de l'investissement max en annee

#chargement du gse exp(cumul?)
ad_GSE<-"/R2 CUBE+/R2 OUT/"
load(paste(paste0(reptravail,"/R_Financyou/GSE+"),ad_GSE,cubecumul,sep=""))
dim(cube_placement)
list_actifs
reptravail<-paste0(reptravail,"/R1 CUBE++")

  NS<-length(cube_placement[,1,1]) # nombre de simulations
  Tp<-length(cube_placement[1,,1]) # maturite des projections

# filtre pour ramener les pas de temps ? 1 an correspondant aux impots
  cube_an<-cube_placement[,seq(1,D/pas_t,1/pas_t),]
  dim(cube_an)
  
  Tp<-D #length(cube_an[1,,1]) # maturite des projections
  
  
#chargement des tables d'impots
  LimkroPV<-50000 #limite pour application de la surtaxe sur PV
  tableau_invest<-read.xlsx(file="./Data_Log/Data/Table_placements.xlsx",sheetIndex = 1)
  tableau_Pinel<-read.xlsx(file="./Data_Log/Data/table_Pinel.xlsx",sheetIndex = 1)
  Ab_pluesvalues<-read.table(file="./Data_Log/Data/Abattement pluesvalues.csv",header = TRUE, sep=";")
  SurtaxePVimmo<-read.table(file="./Data_Log/Data/SurtaxePVimmo.csv",header = TRUE, sep=";")
  Tranche_marginale_IR<-read.table(file="./Data_Log/Data/Tranche_marginale_IR.csv",header = TRUE, sep=";")
  a<-tab_chrono%>%filter(sous.type=="revenu")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  b<-tab_chrono%>%filter(type=="life",sous.type=="part_imp",sous.type_2=="avec projets")%>% select(-type,-sous.type,-sous.type_2)
  Net_imposable<-a/b
  # donnees exterieures annexes ? tester
  tabl_plac<-as.data.frame(hist_$plc[[1]])
  # definition du tableau de resultats
  GSE_plac_taxes<-array(0,dim=c(NS,Tp,D,length(table_placement$nom_plc),2)) #1: Ra ; 2:ra
  
  prod_epar=3
for (prod_epar in 1:length(table_placement$nom_plc)) {
  # donnee par placement
  equi_prod<-which(tableau_invest$placements==table_placement$nom_Tr_GSE1[prod_epar])
  Investmoy<-tabl_plac$Valeur_t0[prod_epar] #investissement moyen retenue
  fees<-tableau_invest$Fees[prod_epar] #frais d'agence + notaire / frais d'entree
  if (tabl_plac$Valeur_t0[prod_epar]!=0) {fees<-0} # bien deja achete
 
# donnees issues du tableau Table_placements
  alpha<-tableau_invest$alpha_div_Frais[prod_epar] # alpha coefficient de frais qui s'applique sur les dividendes
  tau<-tableau_invest$Spread_emprunt[equi_prod] # tau le tau d'emprunt = Inflation + 1.5% sur 20 ans aujourd'hui
  AbTF<-0.5 #abattement pour le calcul de la taxe foncti?re
  tauTFVille<-tableau_invest$Taux_Tf[equi_prod] #taux d'impot foncier apppliqu? par la commune
  PVCS<-0.155 #taux fixe pour les charges sociales
  PVIR<-0.19 #taux fixe pour les impots sur le revenu
  
  alphaFE<-tableau_invest$Alpha_FE[equi_prod] # frais sur encours ex assurance vie
  
  ##### immo avec loyer?
  kro=tableau_invest$Kro1[equi_prod] # =1 si produit un gain direct (mon?taire ou service), =0 sinon (ex: habitation secondaire)
  kro2=tableau_invest$Kro2[equi_prod] # =1 si location ? tierce, 0 si utilisation propre
  N<-tabl_plac$An_rest[prod_epar] # N le nombre d'annee du pret (a remboursement constant)
  Annuite<-tabl_plac$Annuite[prod_epar]
  
  if (Annuite==0) {kro_emp=0} else {kro_emp=1} #verification si emprunt
  
# cube_an le rendement prix cumul? du placement pour D
  # R3D (NS,Tp,D)
  Tr_GSE_Prix<-which(table_invest$Tr_GSE_Prix[which(tabl_plac$nom_Tr_GSE1[prod_epar]==table_invest$placements)]==list_actifs)

  R3D<-array(rep(cube_an[1:NS,1:D,Tr_GSE_Prix],Tp),dim=c(NS,D,Tp)) # on consid?re que le rdt ne depend pas de la date de debut
  R3D<-aperm(R3D,c(1,3,2))

# Fees le frais pr?lev? sur l'invest
  fees3D<-array(rep(fees,NS*Tp*D),dim=c(NS,Tp,D))
  
# TauxIR taux d'IR
  if (tableau_invest$Taux_imp_IR[equi_prod]==0) {Taux_imp_IR<-0 } else
  { Taux_imp_IR<- Tranche_marginale_IR[findInterval(Net_imposable, Tranche_marginale_IR[,1], rightmost.closed = FALSE, all.inside = FALSE,
                 left.open = FALSE),2]
      }
  TauxIR3D<-aperm(array(rep(Taux_imp_IR,NS*D),dim=c(Tp,NS,D)),c(2,1,3))
  
# AbIR abattement surl'IR
  if (tableau_invest$Ab_IR[prod_epar]==1) 
  { AbIR<-1
    AbIR3D<-array(rep(AbIR,NS*Tp*D),dim=c(NS,Tp,D))
  } else {AbIR<-array(0,dim=c(D,1))
      for (i in 1:D) {
        AbIR[i,1]<-Ab_pluesvalues[which(Ab_pluesvalues[,1]>i, arr.ind=TRUE)[1]-1,2]
      }
  AbIR[is.na(AbIR)]<-1
    AbIR3D<-array(rep(AbIR,Tp*NS),dim=c(D,Tp,NS))
    AbIR3D<-aperm(AbIR3D,c(3,2,1))
  }
  
# AbCS abattement sur les CS
  if (tableau_invest$Ab_CS[prod_epar]==0) 
  { AbCS<-0
    AbCS3D<-array(rep(AbCS,NS*Tp*D),dim=c(NS,Tp,D))
  } else {AbCS<-array(0,dim=c(D,1))
    for (i in 1:D) {
      AbCS[i,1]<-Ab_pluesvalues[which(Ab_pluesvalues[,1]>=i, arr.ind=TRUE)[1],3]
    }
  AbCS3D<-array(rep(AbCS,Tp*NS),dim=c(D,Tp,NS))
  AbCS3D<-aperm(AbCS3D,c(3,2,1))
  }
  
# PVIR IR sur les PV positives
  PVIR3D<-array(rep(PVIR,NS*Tp*D),dim=c(NS,Tp,D))
  if (tableau_invest$KroPv[prod_epar]==0)
    {kroPV3D<-array(0,dim=c(NS,Tp,D)) } else 
    { kroPV3D<-array(1,dim=c(NS,Tp,D))
    kroPV3D<-ifelse((R3D/(1+fees))<=1,0,1)
    }
  PVIR3D<-PVIR3D*kroPV3D #tiens compte des PMVL negatives
  rm(kroPV3D)
  
# PVCS CS sur les PV
  PVCS3D<-array(rep(PVCS,NS*Tp*D),dim=c(NS,Tp,D))
  
# TauxCS taux CS
  TauxCS3D<-PVCS3D
  
################################################
  
# alpha coefficient de frais qui s'applique sur les dividendes
  alpha3D<-array(rep(alpha,D*Tp*NS),dim=c(D,Tp,NS))
  alpha3D<-aperm(alpha3D,c(3,2,1))
  
# IiH inflation cumulee propre au dividende et net d'inflation mon?taire sur la periode i ? H
  # IiHcumul<-array(0,dim=c(length(IiH),1))
  # IiHcumul[1]<-IiH[1]
  # for (i in 2:length(IiH)){
  #   IiHcumul[i]<-IiH[i]+IiHcumul[i-1]
  # }
  # IiH3D<-array(rep(IiHcumul,Tp*NS),dim=c(D,Tp,NS))
  # IiH3D<-aperm(IiH3D,c(3,2,1))

# H l'orizon des placements
  H<-seq(1,D, by=1)
  H3D<-array(rep(t(H),Tp*NS),dim=c(D,Tp,NS))
  H3D<-aperm(H3D,c(3,2,1))
  
#definition de kroPV application de la plus value
#calcul vectoriel de la PV
  kroPV=array(0,dim=c(NS,Tp,D)) #=1 si PV superieure a la limite 50 000eur en immo
  #pour un investissement en moyenne
  PVNet<-(R3D/(1+fees)*(1-AbIR3D)-1)*Investmoy
  kroPV<-ifelse(PVNet>LimkroPV,1,0)

  # calcul du taux impot surtaxe immo
  compo<-function (a) {
    compo<-SurtaxePVimmo[which(SurtaxePVimmo[,1]>a, arr.ind=TRUE)[1],2]
  }
  TauxST3D<-array(mapply(compo,PVNet),dim=dim(kroPV))
  TauxST3D<-TauxST3D*1

# formule de calcul du rendement pour un investissement en cash
  Ra<-array(0,dim=c(NS,Tp,D))
  Ra<-R3D/(1+fees)*(1-(1-AbIR3D)*(PVIR3D+kro2*kroPV*TauxST3D)-(1-AbCS3D)*TauxCS3D+(PVIR3D+TauxCS3D+kro2*kroPV*TauxST3D)*(1+fees)/R3D)-alphaFE*aperm(apply(R3D,c(1,2),cumsum),c(2,3,1))
  if (tableau_invest$KroPinel[prod_epar]==1){
    Pinel<-(1:D)
    Pinel<-tableau_Pinel[match(Pinel,tableau_Pinel[,1]),2]
    Pinel[is.na(Pinel)]<-tableau_Pinel[length(tableau_Pinel[,1]),2]
    Ra<-Ra+aperm(array(rep(Pinel,Tp*NS),dim=c(D,Tp,NS)),c(3,2,1))
  }
 
# formule de calcul du rendement annuel pour un investissement par emprunt
    ra<-array(0,dim=c(NS,Tp,D))
    ra<-((1-(1+tau)^(-N))/tau)*(Ra-((1-(1+tau)^(-N+H3D))/(1-(1+tau)^(-N)))) +kro*kro2*(TauxIR3D+TauxCS3D)*(H3D+(1-(1+tau)^(H3D))/(tau*(1+tau)^N)) 
    if (N<D){
    ra[,,N:D]<-((1-(1+tau)^(-N))/tau)*Ra[,,N:D] +kro*kro2*(TauxIR3D[,,N:D]+TauxCS3D[,,N:D])*(N+(1-(1+tau)^N)/(tau*(1+tau)^N)) 
    }
  
# formation des tranche du cube GSE_pls&taxes (N X Tp X D X k pls x 2(Ra et ra) )
  
  GSE_plac_taxes[,,,prod_epar,1]<-Ra
  GSE_plac_taxes[,,,prod_epar,2]<-ra/aperm(array(rep(1:D,NS,Tp),dim=c(D,NS,Tp)),c(2,3,1))
# fin de la boucle sur le invest
}
  
  # mise en forme des resultats avec la liste des placements

  #calcul des correlation entre Ra et ra pour H (horizon de placements) le debut est fix? ? 1
  # cube_cor<-array(apply(GSE_plac_taxes[,1,,],c(2),cor),dim=c(length(GSE_plac_taxes[1,1,1,]),length(GSE_plac_taxes[1,1,1,]),D))
  # cube_EV<-array(0,dim=c(length(GSE_plac_taxes[1,1,1,]),4,D))
  # cube_EV[,1,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),mean)) # esparance E
  # cube_EV[,2,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),sd)) # esparance V
  # cube_EV[,3,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),skewness)) # esparance Skewness
  # cube_EV[,4,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),kurtosis)) # esparance Kurtosis
  
  return(GSE_plac_taxes)
   
} #fin de la fonction
  
  