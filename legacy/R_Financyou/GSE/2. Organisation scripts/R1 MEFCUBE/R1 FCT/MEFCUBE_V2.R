###############
# fct: MEFCUBE_V2.R
###############
#fonction qui met en forme les données générées dans R2 CUBE
#à partir de l'exemple "DonneesMEF_IN.csv"
#
# crée le: 21/12/2017 par Sébastien Gallet
# modifiée le: 21/12/2017 par Sébastien Gallet
#
# Version : 1.1
#
# variables d entree#######################
# Modification du format de sortie (BH modifié) -> entrée de PyBE
###########################################

MefCube <-function(Listcodact,ListNomact,nomsortie)
{

  # Listcodact<-ListCodeactifs
  # ListNomact<-ListNomActifs
  # nomsortie<-"ESG_formatBH.csv"
  N<-length(cube[,1,1])
  pas<-length(cube[1,,1])
  TablesFinal<-array('-',dim=c((N*length(Listcodact)+1),(pas+4)))
  TablesFinal[1,1]<-'CODE'
  TablesFinal[1,2]<-'TRIAL'
  TablesFinal[1,3]<-'PARAMETER'
  TablesFinal[1,4:(pas+3)]<-0:(pas-1)
  i=1
 for (i in 1:N){
   TablesFinal[(2+length(Listcodact)*(i-1)):(2-1+length(Listcodact)*i),1]<-t(Listcodact)
   TablesFinal[(2+length(Listcodact)*(i-1)):(2-1+length(Listcodact)*i),2]<-t(rep(i,length(Listcodact)))
   TablesFinal[(2+length(Listcodact)*(i-1)):(2-1+length(Listcodact)*i),3]<-t(ListNomact)
   TablesFinal[(2+length(Listcodact)*(i-1)):(2-1+length(Listcodact)*i),4:(pas+3)]<-t(cube[i,,]) #utilise la variable cube
 }
  #ajout artificiel de la derniere colonne 120 pour ne pas modifier l'ensemble du code
  TablesFinal[,pas+4]<-TablesFinal[,pas+3]
  TablesFinal[1,pas+4]<-as.character(as.numeric(TablesFinal[1,pas+3])+1)
  
  library("data.table")
  require("data.table")

  # write.table(TablesFinal, file = paste( reptravail,"/R1 OUT/",nomsortie , sep=""),row.names=FALSE, na="",col.names=FALSE,quote=FALSE, sep=";")
  TablesFinal<-as.data.table(TablesFinal)
  fwrite(TablesFinal, file = paste( reptravail,"/R1 MEFCUBE/R1 OUT/",nomsortie , sep=""),sep = ";",
         eol = if (.Platform$OS.type=="windows") "\r\n" else "\n",
         na = "", dec = ".", row.names = FALSE, col.names = FALSE,
         qmethod = c("double"), #,"escape"),
         # logical01 = getOption("datatable.logical01", FALSE),  # due to change to TRUE; see NEWS
         # logicalAsInt = logical01,  # deprecated
         # dateTimeAs = c("ISO","squash","epoch","write.csv"),
         buffMB = 32L, nThread = getDTthreads() )

  #ERASE données inutiles
  rm(list=c('TablesFinal'))
  gc()
}

