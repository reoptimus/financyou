######################################
# Test de martingalité entre deux diffusion HW
#
# Fichier Test_martingal_HW_BS_t0_pays
#
# permet de calculer les kimmo rendant martingale la diffusion HW sur (0,T)
# pour chaque pays de "list_param_pays.Rda"
# martingal / à la diffusion des taux sans risques issu des forwards instantannés EIOPA "EIOPA_avril_2018_FRANCE.xlsx"
#
#Trace le résultat de E[exp(R_immo(0,T))/exp(R_r(0,T))]
######################################

# Tirage aleatoire des taux d'accroissements
periode<-30 # en annnée
delta_t<-0.5 #durée entre 2 periodes de calcul
NB<-1000 #nombre de tirages
nb_periode<-periode/delta_t

rho<-0

set.seed(123)
# tirage des alea UNIQUE
alea_cube<-array(rnorm(NB*nb_periode*4*2),dim=c(NB,nb_periode,4,2))
alea_R1<-alea_cube[,,1,1]
alea_R2<-alea_cube[,,2,1]
alea_R2 <- rho*alea_R1+alea_R2*(1.-rho^2)^0.5
alea_r2<-alea_cube[,,3,1]
alea_r1<-alea_cube[,,4,1]
alea_r2 <- rho*alea_r1+alea_r2*(1.-rho^2)^0.5


## f0t pour pas_t #############################
#chargement de la courbe des taux (EIOPA) et recalcul des courbes f0t et P0t
source("~/Immo/Calib_f0.R")

sc=2
Param_EIOPA<-"EIOPA_avril_2018_FRANCE.xlsx"
Calib_Tauxf0(Param_EIOPA,delta_t,sc)

load(file="~/Immo/Prix_P0t_interp.Rda")
load(file="~/Immo/f0t_liss.Rda")
#plot(f0t_liss)
#################################################
# Chargement des paramètres pays calibrés########
load("~/Immo/list_param_pays.Rda")
#################################################

# Constantes
a1<-0.01
sigma1<-0.008

# objectif parallele: definir la sigmaBS equivalent pour le VaR HW
# presentation en tableau pays vs. periode de VaR
nb_pays=length(list_param_pays[,1])
T_Var=1:20
sigma_BS_equiv<-array(0,dim=c(nb_pays,nb_periode))
VaR_BS<-array(0,dim=c(nb_pays,nb_periode))
VaR_HW<-array(0,dim=c(nb_pays,nb_periode))
theta<-2.58 #VaR 99.5%

j=3 #france
##############################
for (j in 1:nb_pays){ #debut boucle sur les pays
  # Choix du pays
  num_pays<-j
  sigma2<-list_param_pays[num_pays,4] #vol HW immo historique utilisée en RN
  a2<-list_param_pays[num_pays,2] #Viesse de Retour à la Moyenne HW immo historique utilisée en RN
  #r0<-array(rep(list_param_pays[num_pays,3],NB),dim=c(NB))
  r0<-array(rep(f0t_liss[2],NB),dim=c(NB))
  sigmaBS<-sigma2*((1-exp(-2*a2*delta_t))/(2*a2))^0.5 #vol BS immo
  
Tp<-delta_t
tp<-0

R2_R1<-array(0,dim=c(NB,3,nb_periode))
r2_r1<-array(0,dim=c(NB,2,nb_periode))

# Liste du vecteur R2_R1
# 1: Rt taux sans risque HW
# 2: Rt Immo HW par approx normale
# 3: Rt Immo BS, diffusion par BS par apporx normale

# boucle sur les periodes tp, initialisation
k_control<-array(0,dim=c(nb_periode))
k_1<-array(0,dim=c(nb_periode))
r0_2<-r0
r0_1<-r0

for (i in 1:nb_periode) {
  
  #################################
  # Calcul des moy et vol des fonction normale equivaleente des taux d'accroissement
  # r(t) taux court instantanné
  # R(tp,Tp)= N(alpha,eta)
  
  # paramètres pour HW avec k fct(courbe EIOPA) 
  Kt<-(1-exp(-a1*tp))/a1
  KT_t<-(1-exp(-a1*(Tp-tp)))/a1
  if(i==1){
    f0t_prime<-(f0t_liss[i+1]-f0t_liss[i])/delta_t #derivee à droite
  } else{
    f0t_prime<-(f0t_liss[i+2]-f0t_liss[i])/(2*delta_t) #derivee centrée
    #f0t_prime<-(f0t_liss[i+1]-f0t_liss[i])/delta_t #derivee à droite
  }

  k1<-a1*f0t_liss[i+1]+f0t_prime+Kt^2*(sigma1^2)/2
  k_1[i]<-k1
  KT<-(1-exp(-a1*Tp))/a1
  LT<-(sigma1^2*(1-exp(-2*a1*Tp))/(2*a1))
  Lt<-(sigma1^2*(1-exp(-2*a1*tp))/(2*a1))
  
  alpha1<--log(P0t_interp[i+1]/P0t_interp[1])+KT_t^2/2*Lt+KT_t*sigma1^2/2*Kt^2
  eta1<-(KT_t^2*Lt)^0.5
  Rt1<-alpha1+eta1*alea_R1[,i] # calcul vrai entre t et T mais sans propagation entre n et n+1
  r0_1<-f0t_liss[i+1]+sigma1^2/2*KT_t^2+LT^0.5*alea_r1[,i]
  
  ##################################
  # calcul pour BS
  ##################################
  #on en deduit le k2 qui rend martingale 2 par rapport à 1
  etaBS<-sigmaBS*(Tp-tp)^0.5
  muBS<-(alpha1-(etaBS^2+eta1^2)/2+etaBS*eta1*rho+sigmaBS^2/2)/(Tp-tp) #version exact
  #muBS<-r0_1 modèle utilisé couramment
  alphaBS<-(muBS-sigmaBS^2/2)*(Tp-tp)
  RtBS<-alphaBS+etaBS*alea_R2[,i] # BS avec approx normale entre t et T

  ##################################
  # calcul pour HW immo
  ##################################
  K2T<-(1-exp(-a2*Tp))/a2
  K2T2a<-(1-exp(-2*a2*Tp))/(2*a2)
  eta2<-(sigma2/a2)*(Tp-K2T-(a2/2)*K2T^2)^0.5
  # formule qui modifie k à chaque pas de temps pour etre martingal sur la periode
  #kimmo<-(log(P0t_interp[Tp/delta_t+1])+r0_2*K2T+(eta2^2+LT*KT^2-2*rho*eta2*LT^0.5*KT)/2)/(-Tp+K2T)
  kimmo<-(log(P0t_interp[Tp/delta_t+1])+r0_2*K2T+(eta2^2/2))/(-Tp+K2T)
  k_control[i]<-kimmo[1]
  alpha2<-kimmo*Tp+(r0_2-kimmo)*K2T
  Rt2<-alpha2+eta2*alea_R2[,i] # HW avec approx normale entre t et T
  r0_2<-r0_2*exp(-a2*delta_t)+kimmo*(1-exp(-a2*delta_t))+sigma2*sqrt((1-exp(-2*a2*delta_t))/(2*a2))*alea_r2[,i] 

  R2_R1[,,i]<-cbind(Rt1,Rt2,RtBS)
  r2_r1[,,i]<-cbind(r0_1,r0_2)

  # calcul des sigmaBS equivalent à une VaR à tp avec une diffusion HW
    a<--Tp/2
    b<--theta*Tp^0.5
    c<-Tp*muBS-alpha2[1]+theta*eta2
    delta<-b^2-4*a*c
    sigma_BS_equiv[j,i]<-((-b-delta^0.5)/(2*a))/sigmaBS #NB: ici alpha2 constant parcequ'on part de t=0!!!!
    VaR_BS[j,i]<-alphaBS-theta*etaBS
    VaR_HW[j,i]<-alpha2[1]-theta*eta2

  Tp<-Tp+delta_t
  #tp<-tp+delta_t #tp utilise pour les actifs, n'évolue pas au court de la diffusion

} #fin boucle i sur les periodes

#####################
# rendement cumulés
#####################
nb_simu<-dim(R2_R1)[3]
cube_R<-R2_R1

cube_r<-r2_r1*delta_t
for (i in 2:nb_simu) {
  cube_r[,,i]<-cube_r[,,i-1]+(r2_r1[,,i]+r2_r1[,,i-1])/2*delta_t
}


cube_R<-exp(cube_R) # rendement des prix cumulé depuis t0
cube_r<-exp(cube_r)

cube<-cube_R
PrixZC<-1/apply(cube_R[,1,],2,mean)



###############################
# Présentation graphique
###############################
plot(array(1,dim=c(nb_simu,1)),type="l",ylim=c(0,5),xlab="pas_simulation",ylab="Rendements",cex=0.1,
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

plot (k_control,type="l",col="red")

###############################
# Test martingal
###############################
cubeM<-cube[,2,]/cube[,1,] #R2_R1[,2,] : Hull and White    /   R2_R1[,3,] : BS
x<-1:length(cubeM[1,])
max<-apply(cubeM[,],MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(cubeM[,],MARGIN=2,FUN=quantile,probs=0.003)
qet2max<-apply(cubeM[,],MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(cubeM[,],MARGIN=2,FUN=quantile,probs=0.046)
qetmax<-apply(cubeM[,],MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(cubeM[,],MARGIN=2,FUN=quantile,probs=0.317)
#mean<-apply(cube[,],MARGIN=2,FUN=quantile,probs=0.5)
mean<-apply(cubeM[,],MARGIN=2,FUN=mean)

plot(array(1,dim=c(nb_simu,1)),xlim=c(min(x),max(x)),ylim=c(0.1,5),
     xlab="time",ylab="Rate",)
polygon(x=c(x,rev(x)),y=c(max,rev(min)),col="grey",border=NA)
polygon(x=c(x,rev(x)),y=c(qet2max,rev(qet2min)),col="lightblue",border=NA)
polygon(x=c(x,rev(x)),y=c(qetmax,rev(qetmin)),col="blue",border=NA)
lines(x,mean,type="l",col="red")
legend("topleft", inset=.01, title="Qantiles",
       c(expression(3*sigma),expression(2*sigma),expression(sigma),"av."), fill=c("grey","lightblue","blue","red"), horiz=TRUE, cex=0.6)

}#fin de la boucle sur les pays
#####################################

# calcul et mise en forme des VaR equiv
VaR_BS<-exp(VaR_BS)
VaR_HW<-exp(VaR_HW)

Temps_Var_equiv<-array(-1,dim=c(nb_pays,2))
A<-which(VaR_BS<0.75,arr.ind=TRUE) # limite de perte à (1-25%)
for (i in 1:length(A[,1])){
  if(Temps_Var_equiv[A[i,1],1]==-1){
    Temps_Var_equiv[A[i,1],1]=A[i,2]*delta_t
  }
}
A<-which(VaR_HW<0.75,arr.ind=TRUE)
for (i in 1:length(A[,1])){
  if(Temps_Var_equiv[A[i,1],2]==-1){
    Temps_Var_equiv[A[i,1],2]=A[i,2]*delta_t
  }
}
Temps_Var_equiv<-as.data.frame(Temps_Var_equiv)
colnames(Temps_Var_equiv)<-c("BS","HW")
rownames(Temps_Var_equiv)<-list_param_pays[,1]
Temps_Var_equiv

rownames(sigma_BS_equiv)<-list_param_pays[,1]
colnames(sigma_BS_equiv)<-(1:length(sigma_BS_equiv[1,]))*delta_t
sigma_BS_equiv[,c(8,12,16,40)]

plot(sigma_BS_equiv[1,],type="l")
for (i in 1:nb_pays) {
lines(sigma_BS_equiv[i,])
}

