######################################
# Test de martingalité entre deux diffusion HW
#
# Fichier "Test_martingal_HW_BS.R"
#
# suite du fichier "Test_martingal_HW_BS_t0_pays.R"
#
# permet de calculer les kimmo rendant martingale la diffusion HW sur (t,t+1)
# pour chaque pays de "list_param_pays.Rda"
# martingal / à la diffusion des taux sans risques issu des forwards instantannés EIOPA "EIOPA_avril_2018_FRANCE.xlsx"
#
#Trace le résultat de E[exp(R_immo(t,t+1))/exp(R_r(t,t+1))]
######################################

r0_2<-r0
r0_1<-r0

Tp<-delta_t
tp<-0

R2_R1_delta<-array(0,dim=c(NB,5,nb_periode))
cube_cumul<-R2_R1_delta
# Liste du vecteur R2_R1
# 1: Rt taux sans risque HW
# 2: Rt Immo HW par approx normale
# 3: Rt Immo BS, diffusion par BS par apporx normale
# 4: RImmo prix
# 5: RImmo Loyers
Infl<-log(1-0.005)*delta_t # % d'inflation sur les loyers immobiliers hors infl monétaire
L0_P0<-log(1+0.02)*delta_t #% annuel en taux continu
Loyer0<-array(exp(L0_P0),dim=c(NB,1)) # vecteur
#R2_R1_delta[,5,1]<-log(1.02)*delta_t # rendement des loyer à t0

# pour avoir le kimmo il faut lancer "Test_partingal_HW_BS_to pour conserver k_control
k_control_2<-array(0,dim=c(length(k_control)))
kimmoflat<-array(0,dim=c(length(k_control)))

alea_R1<-alea_cube[,,1,2]
alea_R2<-alea_cube[,,2,2]
alea_R2 <- rho*alea_R1+alea_R2*(1.-rho^2)^0.5
alea_r2<-alea_cube[,,3,1] #pas de raison de changer de r2 selon le mode de diffusion
alea_r1<-alea_cube[,,4,1]
alea_r2 <- rho*alea_r1+alea_r2*(1.-rho^2)^0.5
i=1
#################################
# diffusion de R(t) et r(t)
#################################
for (i in 1:(nb_periode-1)) {
  
  # paramètres pour HW avec k fct(courbe EIOPA)
  KT_t<-(1-exp(-a1*delta_t))/a1 
  Lt<-sigma1^2*(1-exp(-2*a1*tp))/(2*a1)
  Kt<-(1-exp(-a1*tp))/a1
  
  if(i==1){
    f0t_prime<-(f0t_liss[i+1]-f0t_liss[i])/delta_t #derivee à droite
  } else{
    f0t_prime<-(f0t_liss[i+2]-f0t_liss[i])/(2*delta_t) #derivee centrée
    #f0t_prime<-(f0t_liss[i+1]-f0t_liss[i])/delta_t #derivee à droite
  }

  Rt1<-(-log(P0t_interp[i+1]/P0t_interp[i]))+KT_t^2/2*Lt-KT_t*(f0t_liss[i]-r0_1)
  r0_1<-f0t_liss[i]+sigma1^2/2+Lt^0.5*alea_r1[,i]

  ##################################
  # calcul pour BS
  ##################################
  #on en deduit le k2 qui rend martingale 2 par rapport à 1
  etaBS<-sigmaBS*(Tp-tp)^0.5
  muBS<-Rt1/delta_t+sigmaBS^2/2 #version exact
  #muBS<-r0_1 #modèle utilisé couramment
  alphaBS<-(muBS-sigmaBS^2/2)*(Tp-tp)
  RtBS<-alphaBS+etaBS*alea_R2[,i] # BS avec approx normale entre t et T
  
  ##################################
  # calcul pour R(t,T) HW immo
  ##################################
  K2T_t2a<-(1-exp(-2*a2*delta_t))/(2*a2)
  K2T_t<-(1-exp(-a2*delta_t))/a2
  eta2<-(sigma2/a2)*(delta_t-2*K2T_t+K2T_t2a)^0.5
  
  ###########################################
  # optimisation de kimmo pour etre martingal
  kimmo<-f0t_liss[i]#-(sigma2^2+sigma1^2)/2#0.02#f0t_prime+a1*f0t_liss[i]+sigma1^2/2*Kt^2#+sigma2^2/2#(0.04/50)*i*delta_t#initialisation
  kimmoflat[i]<-kimmo # uniquement pour tracer
  j=1
  max_j=1000
  pas_k=0.0001
  lim=0.001#erreur acceptée sur E[exp(immo)/exp(TC)]

  # if (i==1) {
  #   correctif<-1
  # } else {
  #     correctif<-mean(exp(cube_cumul[,2,(i-1)])/exp(cube_cumul[,1,(i-1)])) # erreur sur les années disponibles
  # }
  # 
  # diff<-mean(exp(Rt2)/exp(Rt1)*correctif)-1
  # 
  #   while ((abs(diff)>lim) & (j<max_j)) {
  #     correctif<-(correctif-1)/1.5+1 # on cherche a corriger que la moitié de l'erreur
  #   # control du sens de la correction
  #     if (diff>lim) {
  #         kimmo<-kimmo-pas_k*(j)
  #         Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  #         diff2<-mean(exp(Rt2)/exp(Rt1)*correctif)-1
  #         if (abs(diff2)>abs(diff)){ # pas d'amelioration
  #           kimmo<-kimmo+pas_k*(j) # remise à zero
  #           Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  #         } else {
  #           Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  #           diff<-mean(exp(Rt2)/exp(Rt1)*correctif)-1
  #         }
  #     } else {
  #       if (diff<(-lim)) {
  #         kimmo<-kimmo+pas_k*(j)
  #         Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  #         diff2<-mean(exp(Rt2)/exp(Rt1)*correctif)-1
  #         if (abs(diff2)>abs(diff)){ # pas d'amelioration
  #           kimmo<-kimmo-pas_k*(j) # remise à zero
  #           Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  #         } else {
  #           Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  #           diff<-mean(exp(Rt2)/exp(Rt1)*correctif)-1
  #         }
  #       } else{
  #         j=max_j
  #       }
  #     }
  #     re<-10
  #     # control de l'amortissement
  #     if (i>(re+1)){
  #     #kimmo<-((k_control_2[i-2]+k_control_2[i-1])/2+kimmo)/2
  #     # regression liléaire sur
  #     y=k_control_2[(i-re):i]
  #     x=((i-re):i)
  #     kimmo<-(2*(lm(y~x)$coefficients[2]*i+lm(y~x)$coefficients[1])+kimmo)/(3)
  #     }
      
  #Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  #j<-j+1
   # }
  # fin d'optimisation de k(t,t+1) pour etre martingal
  ###########################################

  Rt2<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
  r0_2<-r0_2*exp(-a2*delta_t)+kimmo*(1-exp(-a2*delta_t))+sigma2*K2T_t2a^0.5*alea_r2[,i] 

  k_control_2[i]<-kimmo
  
  R2_R1_delta[,1:3,i]<-cbind(Rt1,Rt2,RtBS)
  ##################################
  # calcul des loyers et prix immo
  # if (i==1){
  #   Infl<-array(Infl,dim=c(NB,1))
  #   Loyer<-Loyer0
  #   R2_R1_delta[,5,i]<-Loyer
  # } else {
  #   Infl<-R2_R1_delta[,1,i-1]
  #   Loyer<-Loyer0-R2_R1_delta[,4,i-1]#+Infl
  #   R2_R1_delta[,5,i]<-Loyer #log(1+exp(Loyer))
  # }
  
  #R2_R1_delta[,4,i]<-log(exp(R2_R1_delta[,2,i])-L0_P0*exp(-cube_cumul[,4,i]+cube_cumul[,1,i]))#prix

  R2_R1_delta[,4,i]<-log(1+L0_P0*exp(-cube_cumul[,2,i]+cube_cumul[,1,i]+i*Infl)) #loyer
  R2_R1_delta[,5,i]<-R2_R1_delta[,2,i]-R2_R1_delta[,4,i] # prix

  ##################################
  
  cube_cumul[,,i+1]<-cube_cumul[,,i]+R2_R1_delta[,,i]

  # calcul de paramètre pour la boucle suivante
  Tp<-Tp+delta_t
  tp<-tp+delta_t #tp utilise pour les actifs, n'évolue pas au court de la diffusion
  
} #fin boucle i sur les periodes

nb_simu<-dim(R2_R1_delta)[3]

#############################################
# choix de la matrice tracée dans la var cube
cube_clean<-cube_cumul
list_elimine<-which(is.nan(cube_clean),arr.ind=1)[,1] # numero des lignes > limite haute
list_elimine<-list_elimine[-which(duplicated(list_elimine))] #liste sans doublons
length(list_elimine)
if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
  cube_clean<-cube_clean[-list_elimine,,]
}



###############################
# Présentation graphique
cube<-exp(cube_clean)
plot(array(1,dim=c(nb_simu,1)),type="l",ylim=c(0,2),xlab="pas_simulation",ylab="Rendements",cex=0.1,
     main=paste("Rendements prix",sep=""), cex.main=0.5,
     las=2,cex.axis=0.6, xaxt = "n")
# solution 1: objectif de diffusion HW = Rt
lines(1:nb_simu,apply(cube[,1,],2,quantile, probs=0.005),type="l", col = 'blue')
lines(1:nb_simu,apply(cube[,1,],2,mean),type="l", lty=2, lwd=1.5, col = 'blue')
# solution 2: objectif de diffusion HW immo
lines(1:nb_simu,apply(cube[,2,],2,quantile, probs=0.005),type="l", col = 'red')
lines(1:nb_simu,apply(cube[,2,],2,mean),type="l", lty=2.5, lwd=2, col = 'red')
# solution 3: objectif de la diffusion BS immo
lines(1:nb_simu,apply(cube[,3,],2,quantile, probs=0.005),type="l", col = 'green')
lines(1:nb_simu,apply(cube[,3,],2,mean),type="l", lty=2, lwd=2, col = 'green')
# solution 3: objectif de la diffusion BS immo
lines(1:nb_simu,apply(cube[,4,],2,quantile, probs=0.005),type="l", col = 'purple')
lines(1:nb_simu,apply(cube[,4,],2,mean),type="l", lty=2, lwd=2, col = 'purple')# solution 3: objectif de la diffusion BS immo
lines(1:nb_simu,apply(cube[,5,],2,quantile, probs=0.005),type="l", col = 'black')
lines(1:nb_simu,apply(cube[,5,],2,mean),type="l", lty=2, lwd=2, col = 'black')
###############################

###############################
# Test martingal
cube<-exp(cube_clean[,5,]+cube_clean[,4,])/exp(cube_clean[,1,]) #R2_R1[,2,] : Hull and White    /   R2_R1[,3,] : BS
cube<-exp(cube_clean[,5,])

x<-1:length(cube[1,])
max<-apply(cube[,],MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(cube[,],MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(cube[,],MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(cube[,],MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(cube[,],MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(cube[,],MARGIN=2,FUN=quantile,probs=0.317)
mean<-apply(cube[,],MARGIN=2,FUN=mean)

plot(array(1,dim=c(nb_simu,1)),type="o",xlim=c(min(x),max(x)),ylim=c(0,5),
     xlab="time",ylab="Rate",)
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")
legend("topleft", inset=.01, title="Qantiles",
       c(expression(3*sigma),expression(2*sigma),expression(sigma),"av."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)
###############################

###############################
# plot de k(0,T) vs. k(t,t+1)
# plot(k_control_2,type="l")
# lines(k_control,col="red")
###############################
#plot(kimmoflat)

# plot(apply(cube[,1,],2,mean),type="l")
# lines(PrixZC,type="l",col="red")
