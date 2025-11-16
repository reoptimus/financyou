###############
# fct: MEFCUBE.R
###############
#fonction qui met en forme les données générées dans R2 CUBE
#à partir de l'exmple "DonneesMEF_IN.csv"
#
# crée le: 02/11/2017 par Sébastien Gallet
# modifiée le: 02/11/2017 par Sébastien Gallet
#
# Version : 1.0
#
# variables d entree#######################
# Utilise le ARRAY cube (var externe) 
# composé de l'ensemble des tranches N X T X NbActif (Attention, très lourd)
###########################################

MefCube <-function(Listcodact,ListNomact,nomsortie)
{
  TablesFinal<-array('-',dim=c((N*length(Listcodact)+11),(T+4)))
  TablesFinal[11,1]<-'Code_Actif'
  TablesFinal[11,2]<-'Trial'
  TablesFinal[11,3]<-'Parameter'
  TablesFinal[11,4:(T+4)]<-0:T
  

 for (i in 1:N){
   TablesFinal[(12+length(Listcodact)*(i-1)):(12-1+length(Listcodact)*i),1]<-Listcodact
   TablesFinal[(12+length(Listcodact)*(i-1)):(12-1+length(Listcodact)*i),2]<-rep(i,length(Listcodact))
   TablesFinal[(12+length(Listcodact)*(i-1)):(12-1+length(Listcodact)*i),3]<-ListNomact
   TablesFinal[(12+length(Listcodact)*(i-1)):(12-1+length(Listcodact)*i),4:(T+3)]<-cube[i,,]
 }

  write.table(TablesFinal, file = paste( reptravail,"/R1 OUT/",nomsortie , sep=""),row.names=FALSE, na="",col.names=FALSE, sep=";")
  
}