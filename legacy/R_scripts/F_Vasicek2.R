#Simulation (l(t+1),r(t+1)) sachant (l(t),r(t)) (distribué selon le processus de Vacisek2)

Vacisek2<-function(TauxLongt,ForceLong,MeanLong,VolatiliteLong,TauxCourtt,ForceCourt,VolatiliteCourt,Norm_LT,Norm_CT,ProjectionFonctionsR) {

# Chargement de Vacisek1.R...
source(paste(reptravail,"/R2 Fonctions locale/F_Vacisek1.R",sep=""))
  
txl=Vacisek1(NS,TauxLongt,ForceLong,MeanLong,VolatiliteLong,Norm_LT)
txc=Vacisek1(NS,TauxCourtt,ForceCourt,TauxLongt,VolatiliteCourt,Norm_CT)

# les resultats sont rangé dans la matrice suivante
txltxc<-cbind(txl,txc);colnames(txltxc)<-c("TauxLong","TauxCourt")
txltxc
}