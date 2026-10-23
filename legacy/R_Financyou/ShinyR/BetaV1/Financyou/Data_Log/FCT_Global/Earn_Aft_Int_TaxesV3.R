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

Earn_Aft_Int_Taxes<-function(tabl_plac,tab_chrono,GSE,pas_t,D,list_placements_compl) {
  
#donnee entree type
  # pas_t<-0.5 # pas du GSE
  # GSE<-cube_placement #Test_ReO.V1.Rda"
  # list_actifs
  # # variables: GSE et list_actifs
  # D<-horiz #(Tp-1) #duree de l'investissement max en annee

#chargement du gse exp(cumul?)
# dim(GSE)
# list_actifs

  NS<-length(GSE[,1,1]) # nombre de simulations
  Tp<-length(GSE[1,,1]) # maturite des projections

# filtre pour ramener les pas de temps ? 1 an correspondant aux impots
  cube_an<-GSE[,seq(1,D/pas_t,1/pas_t),]
  # dim(cube_an)
  
  Tp<-D #length(cube_an[1,,1]) # maturite des projections
  
  
#chargement des tables d'impots
  LimkroPV<-50000 #limite pour application de la surtaxe sur PV
  tableau_invest<-read.xlsx(file="./Data_Log/Data/Table_placements.xlsx",sheetIndex = 1)
  tableau_Pinel<-read.xlsx(file="./Data_Log/Data/Table_Pinel.xlsx",sheetIndex = 1)
  Ab_pluesvalues<-read.table(file="./Data_Log/Data/Abattement pluesvalues.csv",header = TRUE, sep=";")
  SurtaxePVimmo<-read.table(file="./Data_Log/Data/SurtaxePVimmo.csv",header = TRUE, sep=";")
  Tranche_marginale_IR<-tab_IR #read.table(file="./Data_Log/Data/Tranche_marginale_IR.csv",header = TRUE, sep=";")
  a<-tab_chrono%>%filter(sous.type=="revenu")%>% select(-type,-sous.type,-sous.type_2) %>% summarise_all(sum)
  b<-tab_chrono%>%filter(type=="life",sous.type=="part_imp",sous.type_2=="avec projets")%>% select(-type,-sous.type,-sous.type_2)
  Net_imposable<-a/b
  # donnees exterieures annexes ? tester
  
  List_tr_GSE<-tabl_plac$nom_Tr_GSE1[which(tabl_plac$nom_Tr_GSE1!="RAssVie_Eur" & tabl_plac$nom_Tr_GSE1!="Rass_Vie_UC")]
  List_tr_GSE<-c(tabl_plac$nom_Tr_GSE1 ,"RAssVie_Eur","Rass_Vie_UC")
  List_tr_GSE<-unique(List_tr_GSE)
  
  # definition du tableau de resultats
  GSE_plac_taxes<-array(0,dim=c(NS,Tp,D,length(List_tr_GSE),2)) #1: Ra ; 2:ra

for (prod_epar in 1:length(List_tr_GSE)) {
  if (List_tr_GSE[prod_epar]=="RAssVie_Eur" | List_tr_GSE[prod_epar]=="Rass_Vie_UC") {
    if (List_tr_GSE[prod_epar]=="RAssVie_Eur") { nom_tr<-"RAssVie_Eur" } else {nom_tr<-"Rass_Vie_UC"}
    Investmoy<-1
    N<-0 # N le nombre d'annee du pret (a remboursement constant)
    Annuite<-0
  } else {
      nom_tr<-tabl_plac$nom_Tr_GSE1[prod_epar]
      Investmoy<-tabl_plac$Valeur_t0[prod_epar] #investissement moyen retenue
      N<-tabl_plac$An_rest[prod_epar] # N le nombre d'annee du pret (a remboursement constant)
      Annuite<-tabl_plac$Annuite[prod_epar]
      Tr_GSE_Prix<-which(table_invest$Tr_GSE_Prix[which(nom_tr==table_invest$placements)]==list_actifs)
      equi_prod<-which(tableau_invest$placements==nom_tr)
      
      if (tabl_plac$V0_net[prod_epar]!=0 & tabl_plac$type[prod_epar]=="Immobilier") { # plc immmo en cours
        fees<-0 # les frais ont deja ete payes
      } else { # cas general
        fees<-tableau_invest$Fees[equi_prod] #frais d'agence + notaire / frais d'entree
      }
  }
    
    
  #####################################
  # donnee venant de tableau_invest et propre au plc
  alpha<-tableau_invest$alpha_div_Frais[equi_prod] # alpha coefficient de frais qui s'applique sur les dividendes
  tau<-tableau_invest$Spread_emprunt[equi_prod] # tau le tau d'emprunt = Inflation + 1.5% sur 20 ans aujourd'hui
  AbTF<-tableau_invest$Ab_Tf[equi_prod] #abattement pour le calcul de la taxe foncti?re
  tauTFVille<-tableau_invest$Taux_Tf[equi_prod] #taux d'impot foncier apppliqu? par la commune
  PVCS<-tableau_invest$Taux_imp_CS[equi_prod] #taux fixe pour les charges sociales
  PVIR<-tableau_invest$Pv_imp_IR[equi_prod] #taux fixe pour les impots sur le revenu
  alphaFE<-tableau_invest$Alpha_FE[equi_prod] # frais sur encours ex assurance vie
  kro=tableau_invest$Kro1[equi_prod] # =1 si produit un gain direct (mon?taire ou service), =0 sinon (ex: habitation secondaire)
  kro2=tableau_invest$Kro2[equi_prod] # =1 si location ? tierce, 0 si utilisation propre
  kroPinel<-tableau_invest$KroPinel[equi_prod]
  # donne user
 
  if (Annuite==0) {kro_emp=0} else {kro_emp=1} #verification si emprunt
  # tranche du GSE correspondant a prod_epar
  ##############################
  # R3D (NS,Tp,D)
  R3D<-array(rep(cube_an[1:NS,1:D,Tr_GSE_Prix],Tp),dim=c(NS,D,Tp)) # on consid?re que le rdt ne depend pas de la date de debut
  R3D<-aperm(R3D,c(1,3,2))
  # dim(R3D) ; R3D[1:20,10,]

# Fees le frais pr?lev? sur l'invest
  fees3D<-array(rep(fees,NS*Tp*D),dim=c(NS,Tp,D))
  
# TauxIR taux d'IR
  if (tableau_invest$Taux_imp_IR[equi_prod]==0) {Taux_imp_IR<-0 } else
  { Taux_imp_IR<- Tranche_marginale_IR[findInterval(Net_imposable, Tranche_marginale_IR[,1], rightmost.closed = FALSE, all.inside = FALSE,
                 left.open = FALSE),2]
      }
  TauxIR3D<-aperm(array(rep(Taux_imp_IR,NS*D),dim=c(Tp,NS,D)),c(2,1,3))
  
# AbIR abattement sur l'IR
  if (tableau_invest$Ab_IR[equi_prod]==1) 
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
  if (tableau_invest$Ab_CS[equi_prod]==0) 
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
  if (tableau_invest$KroPv[equi_prod]==0)
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
  if (Tr_GSE_Prix==5){ # c'est de l'immobilier
    compo<-function (a) {
      compo<-SurtaxePVimmo[which(SurtaxePVimmo[,1]>a, arr.ind=TRUE)[1],2]
    }
    TauxST3D<-array(mapply(compo,PVNet),dim=dim(kroPV))
    TauxST3D<-TauxST3D*1
  } else { # pas de l'immo, pour gagner du temps
    TauxST3D<-kroPV*0
  }


# formule de calcul du rendement pour un investissement en cash
  Ra<-array(0,dim=c(NS,Tp,D))
  Ra<-R3D/(1+fees)*(1-(1-AbIR3D)*(PVIR3D+kro2*kroPV*TauxST3D)-(1-AbCS3D)*TauxCS3D+(PVIR3D+TauxCS3D+kro2*kroPV*TauxST3D)*(1+fees)/R3D)-alphaFE*aperm(apply(R3D,c(1,2),cumsum),c(2,3,1))
  if (kroPinel==1){
    Pinel<-(1:D)
    Pinel<-tableau_Pinel[match(Pinel,tableau_Pinel[,1]),2]
    Pinel[is.na(Pinel)]<-tableau_Pinel[length(tableau_Pinel[,1]),2]
    Ra<-Ra+aperm(array(rep(Pinel,Tp*NS),dim=c(D,Tp,NS)),c(3,2,1))
  }
 # tr sur les rendements cumul d un eur
  GSE_plac_taxes[,,,which(List_tr_GSE==nom_tr),1]<-Ra # Ra[1:20,10,]
  GSE_plac_taxes[,,,which(List_tr_GSE==nom_tr),2]<-0
  
  ra<-array(0,dim=c(NS,Tp,D)) # dans le cas general, pas de ra, seulement pour l immo
  if (nom_tr=="RimmoPropre" | nom_tr=="RimmoPinel" | nom_tr=="RimmoLoc") {
  # formule de calcul du rendement annuel pour un investissement par emprunt
      if (Annuite!=0) {
        ra<-((1-(1+tau)^(-N))/tau)*(Ra-((1-(1+tau)^(-N+H3D))/(1-(1+tau)^(-N)))) +kro*kro2*(TauxIR3D+TauxCS3D)*(H3D+(1-(1+tau)^(H3D))/(tau*(1+tau)^N)) 
        if (N<D){
        ra[,,N:D]<-((1-(1+tau)^(-N))/tau)*Ra[,,N:D] +kro*kro2*(TauxIR3D[,,N:D]+TauxCS3D[,,N:D])*(N+(1-(1+tau)^N)/(tau*(1+tau)^N)) 
        }
      }
  }
  # tr sur les rendements cumul d un eur rembourse suite a emprunt
  GSE_plac_taxes[,,,which(List_tr_GSE==nom_tr),2]<-ra/aperm(array(rep(1:D,NS,Tp),dim=c(D,NS,Tp)),c(2,3,1))
  ##############################
  } # fin de la boucle sur le invest
  
  # mise en forme des resultats avec la liste des placements

  #calcul des correlation entre Ra et ra pour H (horizon de placements) le debut est fix? ? 1
  # cube_cor<-array(apply(GSE_plac_taxes[,1,,],c(2),cor),dim=c(length(GSE_plac_taxes[1,1,1,]),length(GSE_plac_taxes[1,1,1,]),D))
  # cube_EV<-array(0,dim=c(length(GSE_plac_taxes[1,1,1,]),4,D))
  # cube_EV[,1,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),mean)) # esparance E
  # cube_EV[,2,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),sd)) # esparance V
  # cube_EV[,3,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),skewness)) # esparance Skewness
  # cube_EV[,4,]<-t(apply(GSE_plac_taxes[,1,,],c(2,3),kurtosis)) # esparance Kurtosis
  # apply(GSE_plac_taxes[,10,,,2],c(2,3),mean)
  
  # changement de format du GSE
  GSE<-array(rep(dim(GSE_plac_taxes[,,,1,1]),length(list_placements_compl)),dim=c(dim(GSE_plac_taxes[,,,1,1]),length(list_placements_compl)))
  for (i in 1:length(list_placements_compl)) {
    if (length(grep("crd_",list_placements_compl[i]))!=0) { # c est du crd
      j<-which( List_tr_GSE==sub("crd_","",list_placements_compl[i]))
      if (length(j)!=0) {GSE[,,,i]<-GSE_plac_taxes[,,,j,2]} else {GSE[,,,i]<-0}
    } else {
      j<-which( List_tr_GSE==list_placements_compl[i])
      if (length(j)!=0) {GSE[,,,i]<-GSE_plac_taxes[,,,j,1]} else {GSE[,,,i]<-0}
    }
  }
  # dim(GSE)
  # apply(GSE[,10,10,],c(2),mean)
  
  return(list(GSE,list_placements_compl))
   
} #fin de la fonction
  
  