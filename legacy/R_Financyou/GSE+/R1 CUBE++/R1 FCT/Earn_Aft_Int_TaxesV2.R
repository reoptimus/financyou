#Earning after interests and taxes
#fonction qui prend le cube GSE en entr?e et qui donne le cube GSE_pls&taxes en sorite
# D est la dur?e de l'investissement
# hyp: l'esp?rance des rendements pour une dur?e d'investissement n'?volue pas au cour du temps
###################################
# Modifi?e le 18/04/2019
#
# Entr?e: Cube nom du fichier Rda du GSE
#         reptravail chemin du fichier de travail
# sortie: 3 matrice matrice 2*D (Tp,D) pour E,SD et VaR

####################################################
###  R.A.F.  #######################################
##   preciser les dividendes par type de placements variable sigma
####################################################

Earn_Aft_Int_Taxes<-function(cubecumul,pas_t,D,reptravail,table_placement,Investmoy,Tr_imp,numerotation) {
  
#donnee entree type
  # pas_t<-0.5 # pas du GSE
  # table_placement<-"Table_placements"
  # Investmoy<-200000 #investissement moyen retenue
  # Net_imposable<-80000
  # cubecumul<-"GSE+.Rda" #Test_ReO.V1.Rda"
  # numerotation<-"20200717"
  # titre<-paste0("cas ",numerotation,":invest ",Investmoy/1000,"kEur, Net_imp ",Net_imposable/1000,"kEur")
  # reptravail<-"D:"
  # reptravail<-paste0(reptravail,"/R_Financyou")
  # D<-30 #(Tp-1) #duree de l'investissement

#chargement du gse exp(cumul?)
reptravail<-paste0(reptravail,"/GSE+")
ad_GSE<-"/R2 CUBE+/R2 OUT/"
load(paste(reptravail,ad_GSE,cubecumul,sep=""))
# dim(cube_placement)

reptravail<-paste0(reptravail,"/R1 CUBE++")

  #require(matrixStats)
  #install.packages("matrixStats")
  library(matrixStats)
  library(xlsx)
  library(abind)
  # install.packages("Rtools")
  # install.packages("moments")
  library(moments)
  library(stringr)
  
  NS<-length(cube_placement[,1,1]) # nombre de simulations
  Tp<-length(cube_placement[1,,1]) # maturite des projections

# filtre pour ramener les pas de temps a 1 an correspondant aux impots
  cube_an<-cube_placement[,seq(1,Tp,1/pas_t),]
  dim(cube_an)
  
  Tp<-D+1 #length(cube_an[1,,1]) # maturite des projections
  
  
#chargement des tables d'impots
  # donn?es exterieures annexes ? tester
  LimkroPV<-50000 #limite pour application de la surtaxe sur PV
  
  tableau_invest<-read.xlsx(paste0(reptravail,"/R1 IN/",table_placement,".xlsx"),sheetIndex = 1)
  tableau_Pinel<-read.xlsx(paste0(reptravail,"/R1 IN/table_Pinel.xlsx"),sheetIndex = 1)
  Ab_pluesvalues<-read.table(paste(reptravail,"/R1 IN/Abattement pluesvalues.csv",sep=""),header = TRUE, sep=";")
  SurtaxePVimmo<-read.table(paste(reptravail,"/R1 IN/SurtaxePVimmo.csv",sep=""),header = TRUE, sep=";")
  Tranche_marginale_IR<-read.table(paste(reptravail,"/R1 IN/Tranche_marginale_IR.csv",sep=""),header = TRUE, sep=";")
 
######################
# boucle sur tous les produits d epargne de tableau_invest (environ 14 lignes)
# et g?n?ration du cube4D GSE_pls&taxes (N X Tp X D X 14 pls )
# donnes d entrees: GSE_placements, tableau_invest
######################
  # definition du tableau de resultats
  GSE_plac_taxes<-array(0,dim=c(NS,Tp,D,length(tableau_invest[,1]),4)) # 1: Ra_an ; 2:ra_an ; 3: Ra ; 4:ra
  # tableau pour stocker (E,V)
  mat_EV<-array(0,dim=c(length(tableau_invest$Tr_GSE_Prix),D,4)) # 1: mean RA, 2; sd RA, 3: mean ra, 4: sd ra
  
  # definition de la fonction is.empty
  is.integer0 <- function(x)
  {
    is.integer(x) && length(x) == 0L
  }

#####  boucle sur les produits d'epargnes  #######
  prod_epar=10
for (prod_epar in 1:length(tableau_invest[,1])) {

# donnees issues du tableau Table_placements
  fees<-tableau_invest$Fees[prod_epar] #frais d'agence + notaire / frais d'entree
  
  tr_div<-which(list_actifs==tableau_invest$Tr_GSE_Div[prod_epar])
  if (is.integer0(tr_div)) {
    sigma<-array(tableau_invest$Taux_div[prod_epar],dim=c(NS,Tp))
  } else {
    #sigma<-log(cube_an[,,which(list_actifs==tableau_invest$Tr_GSE_Div[prod_epar])]) # sigma le taux de dividende 
    sigma<-array(Taux_loyer,dim=c(NS,Tp)) # rdt flat des loyers de 3% du prix d'achat constant dans le temps hors inflation depend de la region
  }

  alpha<-tableau_invest$alpha_div_Frais[prod_epar] # alpha coefficient de frais qui s'applique sur les dividendes
  tau<-tableau_invest$Spread_emprunt[prod_epar] # tau le tau d'emprunt = Inflation + 1.5% sur 20 ans aujourd'hui
  AbTF<-tableau_invest$Ab_Tf[prod_epar] #0.5 #abattement pour le calcul de la taxe foncti?re
  tauTFVille<-tableau_invest$Taux_Tf[prod_epar] #taux d'impot foncier apppliqu? par la commune
  PVCS<-tableau_invest$Taux_imp_CS[prod_epar] #0.155 #taux fixe pour les charges sociales
  PVIR<-tableau_invest$Pv_imp_IR[prod_epar] #0.19 #taux fixe pour les impots sur le revenu
  
  alphaFE<-tableau_invest$Alpha_FE[prod_epar] # frais sur encours ex assurance vie
  ##### immo avec loyer?
  kro=tableau_invest$Kro1[prod_epar] # =1 si produit un gain direct (mon?taire ou service), =0 sinon (ex: habitation secondaire)
  kro2=tableau_invest$Kro2[prod_epar] # =1 si location ? tierce, 0 si utilisation propre
  N<-tableau_invest$annee_empr[prod_epar] # N le nombre d'annee du pret (a remboursement constant)
  if (N==0) {kro_emp=0} else {kro_emp=1} #verification si emprunt
  
# cube_an le rendement prix cumul? du placement pour D
  # R3D (NS,Tp,D)
Tr_GSE_Prix<-which(list_actifs==tableau_invest$Tr_GSE_Prix[prod_epar])
 R3D<-array(rep(cube_an[1:NS,1:D,Tr_GSE_Prix],Tp),dim=c(NS,D,Tp)) # on consid?re que le rdt ne depend pas de la date de debut
 R3D<-aperm(R3D,c(1,3,2))

# Fees le frais pr?lev? sur l'invest
  fees3D<-array(rep(fees,NS*Tp*D),dim=c(NS,Tp,D))
  
# TauxIR taux d'IR
  # if (tableau_invest$Taux_imp_IR[prod_epar]==0) 
  # {Taux_imp_IR<-0 } else
  # { if (Net_imposable>Tranche_marginale_IR[length(Tranche_marginale_IR[,1]),1]) {
  #   Taux_imp_IR<-Tranche_marginale_IR[length(Tranche_marginale_IR[,1]),2]
  #   } else
  #   {Taux_imp_IR<-Tranche_marginale_IR[which(Tranche_marginale_IR[,1]>Net_imposable, arr.ind=TRUE)[1]-1,2]  }
  # }
  Taux_imp_IR<-Tr_imp # le taux marginal IR est une donnee externe
  TauxIR3D<-array(rep(Taux_imp_IR,NS*Tp*D),dim=c(NS,Tp,D))
  
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
# sigma le taux de dividende (en % de l'achat ? t=0)
# A modifier, doit d?pendre du fichier.csv des placements
  sigma3D<-array(0,dim=c(NS,Tp,D))
  sigma3D[,,1]<-sigma[,]
  for (i in 2:D){
    #sigma3D[,1:(Tp-i+1),i]<-sigma3D[,i:Tp,i]+sigma3D[,1:(Tp-i+1),i-1]
    sigma3D[,,i]<-sigma+sigma3D[,,i-1]
  }
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
  Ra<-R3D/(1+fees)*(1-(1-AbIR3D)*(PVIR3D+kro2*kroPV*TauxST3D)-(1-AbCS3D)*TauxCS3D+(PVIR3D+TauxCS3D+kro2*kroPV*TauxST3D)*(1+fees)/R3D)+sigma3D*(kro*(alpha3D-kro2*(TauxIR3D+TauxCS3D)*(2*alpha3D-1))-(1-AbTF)*tauTFVille)-alphaFE*aperm(apply(R3D,c(1,2),cumsum),c(2,3,1))
  if (tableau_invest$KroPinel[prod_epar]==1){
    Pinel<-(1:D)
    Pinel<-tableau_Pinel[match(Pinel,tableau_Pinel[,1]),2]
    Pinel[is.na(Pinel)]<-tableau_Pinel[length(tableau_Pinel[,1]),2]
    Ra<-Ra+aperm(array(rep(Pinel,Tp*NS),dim=c(D,Tp,NS)),c(3,2,1))
  }
  # calcul du rendement annuel moyen sur le D considere
  R3D_an<-sign(R3D)*abs(R3D)^(1/H3D)
  Ra_an<-sign(Ra)*abs(Ra)^(1/H3D)  #ATTENTION pb quand les coef rendement <0
  # dim(Ra_an)
  # apply(Ra_an,c(2,3),mean)

# formule de calcul du rendement annuel pour un investissement par emprunt
  ra<-array(0,dim=c(NS,Tp,D))
  ra_an<-array(0,dim=c(NS,D,Tp))
  if (N==0) {ra_an<-aperm(ra_an,c(1,3,2))} else {
    ra<-((1-(1+tau)^(-N))/tau)*(Ra-((1-(1+tau)^(-N+H3D))/(1-(1+tau)^(-N)))) +kro*kro2*(TauxIR3D+TauxCS3D)*(H3D+(1-(1+tau)^(H3D))/(tau*(1+tau)^N)) 
    if (N<D){
    ra[,,N:D]<-((1-(1+tau)^(-N))/tau)*Ra[,,N:D] +kro*kro2*(TauxIR3D[,,N:D]+TauxCS3D[,,N:D])*(N+(1-(1+tau)^N)/(tau*(1+tau)^N)) 
    }
  
  # calcul du rendement annuel moyen sur le D considere
  ra_an2<-array(0,dim=c(NS,D))
  low<--1 #limite pour trouver le root
  up<-5 #limite pour trouver le root
    for (j in 1:D) {
      ra_an2[,j]<-ifelse(ra[,1,j]>1,1,-1)
      ra_an[,j,1]<- sapply(ra[,1,j],function(x) uniroot(function(y,x) ((1-y^(H3D[1,1,j]+1))/(1-y)-(abs(x-1)+1)),  lower=low , upper= up, x=x)$root)
    }
  ra_an[,,1]<-ra_an[,,1]*ra_an2[,]
  ra_an[,,]<-rep(ra_an[,,1],Tp) #on consid?re le rendement identique quelque soit l'annee de debut du placement
  ra_an<-aperm(ra_an,c(1,3,2))

    
   }
  
# formation des tranche du cube GSE_pls&taxes (N X Tp X D X k pls x 2(Ra et ra) )
  
  GSE_plac_taxes[,,,prod_epar,1]<-Ra_an
  GSE_plac_taxes[,,,prod_epar,2]<-ra_an
  GSE_plac_taxes[,,,prod_epar,3]<-Ra
  GSE_plac_taxes[,,,prod_epar,4]<-ra/aperm(array(rep(1:D,NS,Tp),dim=c(D,NS,Tp)),c(2,3,1))
# fin de la boucle sur le invest
}
  
  
  # mise en forme des resultats avec la liste des placements
  list_placements<-c(as.character(tableau_invest$placement) ,str_c("crd_",tableau_invest$placement[which(tableau_invest$annee_empr!=0)]))
  list_num_crd<-tableau_invest$ID[which(tableau_invest$annee_empr!=0)]
  GSE_plac_taxes_an<-(abind(GSE_plac_taxes[,,,,1],GSE_plac_taxes[,,,list_num_crd,2],along=4)) # N , Tp , D , Actifs
  GSE_plac_taxes_cuml<-(abind(GSE_plac_taxes[,,,,3],GSE_plac_taxes[,,,list_num_crd,4],along=4))
  
  #calcul des correlation entre Ra et ra pour H (horizon de placements) le debut est fix? ? 1
  # cube_cor<-array(apply(GSE_plac_taxes[,1,,],c(2),cor),dim=c(length(GSE_plac_taxes[1,1,1,]),length(GSE_plac_taxes[1,1,1,]),D))
  # cube_EV<-array(0,dim=c(length(GSE_plac_taxes[1,1,1,]),4,D))
  # cube_EV[,1,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),mean)) # esparance E
  # cube_EV[,2,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),sd)) # esparance V
  # cube_EV[,3,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),skewness)) # esparance Skewness
  # cube_EV[,4,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),kurtosis)) # esparance Kurtosis
  
  save(GSE_plac_taxes_an,GSE_plac_taxes_cuml,list_placements,file=paste0(reptravail,"/R1 OUT/","GSE++_",numerotation,".Rda"))
  # load(file=paste0(reptravail,"/R1 OUT/","GSE++_",numerotation,".Rda"))
  # save(GSE_plac_taxes_cuml,titre,list_placements,file=paste0(reptravail,"/R1 OUT/","GSE++_",numerotation,".Rda"))
  # 
   rm(list=ls(all=TRUE))
   gc()
   
} #fin de la fonction
  
  