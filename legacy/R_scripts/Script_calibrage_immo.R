###############
# fct: calibrage_immo
###############
#fonction qui calcul la volatilité des données immo
#
# crée le: 09/05/2018 par Sébastien Gallet
# modifiée le: 09/05/2018 par Sébastien Gallet
#
# Version : 1
#
# variables d entree#######################
# repertoire de travail pour trouver la données Rdt_Immobilier
###########################################

calibrage_immo <- function(repertravail,nomfichiertxt)
{ #debut fonction
  repertravail<-"//intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts/R4 CALIBRAGE/R4 IN"
  nomfichiertxt<-"Rdt_immo_Paris_horsinfla_INSEE_20172510"
  setwd(repertravail)
  
Rdt_Immobilier<-scan(paste(nomfichiertxt,".txt", sep=""))
#Définition du nombre d'observation dans le fichier en entrée
Nobs<-length(Rdt_Immobilier)
#Définition des séries
Rdt_Immobilier_tplusun=Rdt_Immobilier[2:Nobs]
Rdt_Immobilier_t=Rdt_Immobilier[1:(Nobs-1)]
#Régression par les MCO
reg_Rdt_Immobilier=lm(Rdt_Immobilier_tplusun~Rdt_Immobilier_t)
Resid_Rdt_Immobilier=resid(reg_Rdt_Immobilier)/(sd(resid(reg_Rdt_Immobilier))*sqrt((Nobs-2)/(Nobs-3)))
Resid_Rdt_Immobilier=Resid_Rdt_Immobilier[2:(Nobs-1)] #residus standardisés en sigma

#summary(reg_Rdt_Immobilier)
#plot(resid(reg_Rdt_Immobilier))
#plot(reg_Rdt_Immobilier)

#volatilité immo est ici assimilée à la sd des résidus d'un modèle linéaire
vol_immo<-sd(resid(reg_Rdt_Immobilier))