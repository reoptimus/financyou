 ############################
  #
  # fct intermediaire du calcul d optimum
  #
  # le 31/10/2020
  # V1.0
  # par SG
  ############################

 optim_tang<-function(i,apport_floue,annuite_floue,horiz) {
   ##########################
  # definition de la meilleure solution en terme de couverture d air
   # i=3
  pt_deb<-(apport_floue+annuite_floue)[i]
  
  # calcul des angles
  
  # distance<-(seq(1,horiz,1)^2+((apport_floue[i:(horiz+i-1)]+annuite_floue[i:(horiz+i-1)]-pt_deb)/max(apport_floue[i:(horiz+i-1)]+annuite_floue[i:(horiz+i-1)]-pt_deb)*horiz)^2)^0.5
  distance<-( seq(0,(horiz-1),1)^2+
                ( (apport_floue[i:(horiz+i-1)]+annuite_floue[i:(horiz+i-1)]-pt_deb)
                  /
                    max(apport_floue[i:(horiz+i-1)]+annuite_floue[i:(horiz+i-1)])*horiz)^2)^0.5
  
  cos_angle<-seq(0,(horiz-1),1)/distance # cos
  cos_angle<-cos_angle[-1]
  # plot(1/(cos_angle))
  # on retire les deux plus petit-> on autorise a ne pas respecter les regles pendant 2 ans
  if ((max(cos_angle)!=min(cos_angle)) && (!is.na(cos_angle)) ) {cos_angle<-cos_angle[-which(cos_angle==max(cos_angle))]}
  if ((max(cos_angle)!=min(cos_angle)) && (!is.na(cos_angle))) {cos_angle<-cos_angle[-which(cos_angle==max(cos_angle))]}
  # if (max(cos_angle)!=min(cos_angle)) {cos_angle<-cos_angle[-which(cos_angle==max(cos_angle))]}
  # annuite<-((1/max(cos_angle))^2-1)^0.5*max(apport_floue[i:(horiz+i-1)]+annuite_floue[i:(horiz+i-1)]-pt_deb)/horiz
  annuite<-((1/max(cos_angle))^2-1)^0.5*max(apport_floue[i:(horiz+i-1)]+annuite_floue[i:(horiz+i-1)])/horiz
  
  # calcul du volume
  ratio_air<-sum(c(rep(0,i),pt_deb+seq(1,(horiz-i),1)*annuite))/sum(apport_floue[1:(horiz)]+annuite_floue[1:(horiz)])
  # plot(1:horiz,(pt_deb+seq(0,(horiz-1),1)*annuite),col="blue",ylim=c(0,500000))
  # lines(1:horiz,(apport_floue[i:(horiz+i-1)]+annuite_floue[i:(horiz+i-1)]),col="red")
  
  return(list(ratio_air,annuite,pt_deb))
}