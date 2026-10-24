#######################
#
# constitution des donnees au format nested data.frame
#
# cree le 28/01/2020
library(tidyr)
# variables hat
reptravail<-"E:"
reptravail<-paste0(reptravail,"/R_Financyou")
table_invest_t0<-read.xlsx(paste0(reptravail,"/MOCA/IN/","Table_placements_t0",".xlsx"),sheetIndex = 1)
# correction de valeurt0 pour les credits en cours
Rest_crd<-table_invest_t0$Annuite*(1-(1+table_invest_t0$Taux)^(-table_invest_t0$An_rest))/table_invest_t0$Taux
table_invest_t0$Valeur_t0[which(table_invest_t0$Annuite!=0)]<-table_invest_t0$Valeur_t0[which(table_invest_t0$Annuite!=0)]-Rest_crd[which(table_invest_t0$Annuite!=0)]

#as.data.frame(table_invest_t0)
BDD <- as.data.frame(setNames(replicate(7,numeric(0), simplify = F),c("pseudo","pass","fiche","revenu","plc","avers","projets") ))
ajout<-as.data.frame(t(rep(0,length(names(BDD)))) )
names(ajout)<-names(BDD)
for (i in 1:length(unique(user_projets$User_ID))){
  BDD<-rbind(BDD,ajout)
}
# user_projets<-user_projets[,-1]
if (sum(BDD$pseudo=="")!=0) {
  BDD<-BDD[-which(BDD$pseudo==""),]
}

BDD$pseudo<-suppressWarnings((user_projets %>% nest(-User_ID))$User_ID)
BDD$projets<-suppressWarnings((user_projets %>% nest(-User_ID))$data)
# dummy<-as.data.frame(unnest(BDD,"projets"))
# names(dummy)
# dummy[dummy$pseudo=="test",]

# Revenu
Net_imposable<-40000
taux_eparg<-0.15
Loyer<-800*12
revenu<-as.data.frame(t(c(Net_imposable,taux_eparg,Loyer)))
names(revenu)<-c("Net_imposable","taux_eparg","Loyer")
nest(revenu,data=c("Net_imposable","taux_eparg","Loyer"))
BDD$revenu[1]<-nest(revenu,data=c("Net_imposable","taux_eparg","Loyer"))

#placements
BDD$plc[1]<-nest(as.data.frame(table_invest_t0),data=everything())
#recuperation de la donnee
oto<-as.data.frame(as.list(unnest((BDD[1,]),cols=c("revenu"))$revenu))


save(BDD,file=paste0(reptravail,"/ShinyR/BetaV0/Financyou/Data_Log/BDD.Rda"))

#ajouter des lignes a BDD
BDD<-bind_rows(BDD,BDD[1,])

# ecrire un pseudo
BDD$pseudo[3]<-"test1"
# ecrire un revenu
BDD[1,"revenu",drop=TRUE]
a<-as.data.frame( t(c(4.1e+04,1.6e-01,10e+03)) )
names(a)<-c("Net_imposable","taux_eparg","Loyer")
BDD[1,"revenu"]<-nest(a,data = everything())
# ecrire plc
BDD[1,"plc",drop=TRUE]
class(table_invest_t0) # format data.frame
BDD[1,"plc"]<-nest(table_invest_t0,data = everything())
# ecrire projets
BDD[1,"projets"]<-nest(a,data = everything())

a<-array(0,dim=c(4,6))
colnames(a)<-c("Nom","Debut","Versement","Mensualite","Duree","Revente")
a<-as.data.frame(a)
class(a$Nom)<-"character"
class(a$Debut)<-"numeric"
class(a$Versement)<-"numeric"
class(a$Mensualite)<-"numeric"
class(a$Duree)<-"numeric"
class(a$Revente)<-"numeric"

class(user_projets$Mensualite)<-"numeric"
class(user_projets$Duree)<-"numeric"


b<-as.data.frame(array(0,dim=c(1,7)))
names(b)<-c("Loyer","proprietaire","fini.payer","Montant.bien","an_tot","an_rest","taux_crd_immo")
class(b$proprietaire)<-"logical"
class(b$fini.payer)<-"logical"
apply(b,2,class)
BDD[1,"fiche"]<-nest(b,data=everything())