###############
# fct: HullWhite PMR
###############
#fonction qui genere les taux courts de la formule d'Hull-White, le deflateur et le cube des browniens correlés
#servant de base aux autres calculs (Immo/action)
#à partir des paramètres calibrés
#
# crée le: 7/12/2017 par Fabrice Borel-Mathurin
# modifiée le: 02/01/2019 par Sebastien G.
#
# Version : 2
#
# variables d entree#######################
# param_calib = fichier Rdata contenant les paramètres calibrés de la fonction de Vasicek
# Mat_res = Matrice des residus correlés Epsilon
#               3 paramètres:k, VolHW, f (taux forward instantanés f(0,t))
# nom_sortie = nom donne a la variable de sortie, ici une tranche du cube
# nom_sortie_defl = nom donne a la variable de sortie de la tranche des déflateurs
# pas_t = pas de temps de sortie des resulstats définitifs
# pas_discr = pas de temps de calcul interne
###########################################
print("Debut du calcul de Rt et deflateur")
flush.console()
library(xlsx)
HullWhite <- function(param_calib , Param_EIOPA , sc , nom_corr_csv , nom_sortie_Rt , nom_sortie_defl , nom_sortie_cubealea , N,Tf,pas_t,pas_discr,reptravail,lim_h,lim_b,pas_PMR)
{
  
  # Paramètres figés pour démonstration
  # param_calib<-"a_sigma_V3.Rda"
  # nom_sortie_Rt<-"Tr-Rt"
  # nom_sortie_defl<-"Tr-deflator"
  # N=500
  # Tf=40
  # pas_discr<-0.005
  # pas_t<-0.5
  # Param_EIOPA<-"EIOPA_avril_2018_FRANCE.xlsx"
  # nom_corr_csv="Corr_ResidAhlgrim_V2.xlsx"
  # nom_sortie_cubealea="Epsilon.Rda"
  # lim_h=1
  # lim_b=-0.5
  # pas_PMR<-0.5
  # sc= 2 #donnée EIOPA baseline
  reptravail<-getwd()
  reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")

  # Chargement des fonctions utilisées
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rt_HullWhite.R",sep=""))
  source(paste(reptravail,"/R4 CALIBRAGE/R4 FCT/Prime_risque_Caja.R",sep=""))
  source(paste(reptravail,"/R3 CUBE ALEA/R3 FCT/cubealea_V5.R",sep=''))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rdtcumul.R",sep=""))
  
  # calcul de la PMR sur pas-discr
  PMR_func(pas_discr,Tf,N,reptravail,"PMR",pas_PMR)   

  #PMR_func(pas_t,Tf,N,reptravail)
  #chargement des parametres H&W a et sigma et PMR
  load(paste(reptravail,"/R2 CUBE/R2 IN/",param_calib, sep="") )
  load(paste(reptravail,"/R2 CUBE/R2 IN/PMR.Rda", sep="") )
  # test sur MPR
  #PMR<-PMR/PMR*1

  #definition de la taille des matrices
  nb_pas<-Tf/pas_discr

  ## f0t pour pas_discr #############################
  #chargement de la courbe des taux (EIOPA) et recalcul des courbes f0t et P0t
  source(paste(reptravail,"/R4 CALIBRAGE/R4 FCT/","Calib_Tauxf0_V2.2.R",sep=""))
  Calib_Tauxf0(Param_EIOPA,reptravail,pas_discr,sc)
  load(paste(reptravail,"/R4 CALIBRAGE/R4 OUT/f0t_liss_",sc,".Rda",sep=""))
  f0t_interp<-t(f0t_liss)
  f0t_interp<- f0t_interp[(1:nb_pas)]
  load(paste(reptravail,"/R4 CALIBRAGE/R4 OUT/Prix_P0t_interp_",sc,".Rda",sep=""))
  ###################################################

  ##################################
  # Production de Rt (taux instantanés)
  ########################
 
  # Chargement des fonctions utilisées L() et K()
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_K_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_L_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rt_HullWhite.R",sep=""))
  
  
  ###############################################
  #Simulations du taux court Rt  pour toutes les périodes de projection
  ###############################################
  # tirage des aléa de Rt
  Mat_resid<-array(rnorm(N/2*nb_pas,0,1),dim=c(N/2,nb_pas))
  Mat_resid<-rbind(Mat_resid,-Mat_resid)

  #Initialisation 
  Rt<-matrix(0,nrow=N,ncol=nb_pas)
  Rt_PMR<-matrix(0,nrow=N,ncol=nb_pas)
  rt<-matrix(0,nrow=N,ncol=nb_pas)
  rt_PMR<-matrix(0,nrow=N,ncol=nb_pas)
  
  #Initialisation 
  Tp<-pas_discr
  tp<-0

  for(i in 1:(nb_pas-1)){
    #Utilisation des formules discrétisées de Hull-White
    # Rt[,i+1]<-Rt_HW(i,Rt[,i],a,sigma,f0t_interp,Mat_resid[,i],pas_discr)
    # Rt_PMR[,i+1]<-Rt[,i+1]+sigma*K(pas_discr,a)*PMR[,i] # faux!!!!!
    # 
    #a modifier pour k= +PMR
    rt[,i+1]<-rt[,i]*exp(-a*pas_discr)+f0t_liss[i+1]-f0t_liss[i]*exp(-a*pas_discr)+sigma^2/2*(K(Tp,a)^2-exp(-a*pas_discr)*K(tp,a)^2)+L(pas_discr,sigma,a)^0.5*Mat_resid[,i]
    rt_PMR[,i+1]<-rt[,i]+PMR[,i+1]*sigma*(1-exp(-a*pas_discr))/a
    #rt_PMR[,i+1]<-rt[,i]*exp(-a*pas_discr)+f0t_liss[i+1]-PMR[,i+1]*sigma-(f0t_liss[i]-PMR[,i]*sigma)*exp(-a*pas_discr)+sigma^2/2*(K(Tp,a)^2-exp(-a*pas_discr)*K(tp,a)^2)+L(pas_discr,sigma,a)^0.5*Mat_resid[,i]
     Rt[,i+1]<-(-log(P0t_interp[i+1]/P0t_interp[i]))+K(pas_discr,a)^2/2*L(tp,sigma,a)-K(pas_discr,a)*(f0t_liss[i]-rt[,i])
     Rt_PMR[,i+1]<-(-log(P0t_interp[i+1]/P0t_interp[i]))+K(pas_discr,a)^2/2*L(tp,sigma,a)-K(pas_discr,a)*(f0t_liss[i]-rt_PMR[,i]) #-PMR[,i+1]*sigma
    # 
    Tp<-Tp+pas_discr
    tp<-tp+pas_discr
    }
  print("fin de calcul de Rt")
  flush.console()
  
  plot(apply(Rt,2,mean),ylim=c(-0.01,0.02),type="l",main="Rt avec/sans PMR")
  lines(apply(Rt,2,quantile, probs=c(0.005,0.995))[1,],col="red")
  lines(apply(Rt,2,quantile, probs=c(0.005,0.995))[2,],col="blue")
  lines(apply(Rt_PMR,2,mean),col="green")
  lines(apply(Rt_PMR,2,quantile, probs=c(0.005,0.995))[1,],col="purple")
  lines(apply(Rt_PMR,2,quantile, probs=c(0.005,0.995))[2,],col="brown")

  
  ###############################################
  # Contrôl des taux explosifs
  ###############################################
  print("contrôl des taux explosifs")
  flush.console()
  
  # transformation en taux continu
  lim_h<-log(lim_h+1)
  lim_b<-log(lim_b+1)
  
  # repérage et élimination des scénario sup ou inf (au moins une fois) aux valeurs limites
  # limite haute
  list_elimine<-which(Rt>lim_h,arr.ind=1)[,1] # numero des lignes > limite haute
  list_elimine_PMR<-which(Rt_PMR>lim_h,arr.ind=1)[,1]
  list_elimine<-c(list_elimine,list_elimine_PMR)
  list_elimine<-list_elimine[-which(duplicated(list_elimine))] #liste sans doublons
  if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
    Rt<-Rt[-list_elimine,]
    rt<-rt[-list_elimine,]
    Rt_PMR<-Rt_PMR[-list_elimine,]
    rt_PMR<-rt_PMR[-list_elimine,]
    PMR<-PMR[-list_elimine,]
  }
  
  # limite basse
  list_elimine<-which(Rt<lim_b,arr.ind=1)[,1] # numero des lignes < limite basse
  list_elimine_PMR<-which(Rt_PMR<lim_b,arr.ind=1)[,1]
  list_elimine<-c(list_elimine,list_elimine_PMR)
  list_elimine<-list_elimine[-which(duplicated(list_elimine))] #liste sans doublons
  if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
    Rt<-Rt[-list_elimine,]
    rt<-rt[-list_elimine,]
    Rt_PMR<-Rt_PMR[-list_elimine,]
    rt_PMR<-rt_PMR[-list_elimine,]
    PMR<-PMR[-list_elimine,]
  }
  #dim(Rt)
  
  N_exp<-as.numeric(dim(Rt)[1])
  diff_N<-ceiling((N-N_exp)/2)*2
  print(paste("% de scénario retirés: ",diff_N/N,sep=""))
  flush.console()
  
  if (diff_N>N/2) { 
    print(paste("% de scénario à retirer > 50% du tirage initial: ",diff_N/N," -> annulation du filtre",sep=""))
    flush.console()
    } else {
    while (diff_N>0) {
      Rt_diff<-matrix(0,nrow=diff_N,ncol=nb_pas)
      Rt_diff_PMR<-matrix(0,nrow=diff_N,ncol=nb_pas)
      rt_diff<-matrix(0,nrow=diff_N,ncol=nb_pas)
      rt_diff_PMR<-matrix(0,nrow=diff_N,ncol=nb_pas)
      #tirage des residus aleatoire      
      Mat_resid<-array(rnorm(diff_N/2*nb_pas,0,1),dim=c(diff_N/2,nb_pas))
      Mat_resid<-rbind(Mat_resid,-Mat_resid)
      # il faut retirer des PMR
      PMR_func(pas_discr,Tf,diff_N,reptravail,"PMR_diff")
      load(paste(reptravail,"/R2 CUBE/R2 IN/PMR_diff.Rda", sep="") )
      
      #Initialisation 
      Tp<-pas_discr
      tp<-0
      
      for(i in 1:(nb_pas-1)){
        #Utilisation des formules discrétisées de Hull-White
        # Rt_diff[,i+1]<-Rt_HW(i,Rt_diff[,i],a,sigma,f0t_interp,Mat_resid,pas_discr) 
        # Rt_diff_PMR[,i+1]<-Rt_diff[,i+1]+PMR[i]*sigma*K(pas_discr,a)
         rt_diff[,i+1]<-rt_diff[,i]*exp(-a*pas_discr)+f0t_liss[i+1]-f0t_liss[i]*exp(-a*pas_discr)+sigma^2/2*(K(Tp,a)^2-exp(-a*pas_discr)*K(tp,a)^2)+L(pas_discr,sigma,a)^0.5*Mat_resid[,i]
         rt_diff_PMR[,i+1]<-rt_diff[,i]+PMR[,i+1]*sigma*(1-exp(-a*pas_discr))/a
         Rt_diff[,i+1]<-(-log(P0t_interp[i+1]/P0t_interp[i]))+K(pas_discr,a)^2/2*L(tp,sigma,a)-K(pas_discr,a)*(f0t_liss[i]-rt_diff[,i])
         Rt_diff_PMR[,i+1]<-(-log(P0t_interp[i+1]/P0t_interp[i]))+K(pas_discr,a)^2/2*L(tp,sigma,a)-K(pas_discr,a)*(f0t_liss[i]-rt_diff_PMR[,i])#-PMR[,i+1]*sigma
         Tp<-Tp+pas_discr
         tp<-tp+pas_discr
      }
      if (is.na(mean(which(Rt_diff>lim_h,arr.ind=1)[,1])) | is.na(mean(which(Rt_diff<lim_b,arr.ind=1)[,1])) | is.na(mean(which(Rt_diff_PMR>lim_h,arr.ind=1)[,1])) | is.na(mean(which(Rt_diff_PMR<lim_b,arr.ind=1)[,1]))) {
      } else {
        # limite haute
        list_elimine<-which(Rt_diff>lim_h,arr.ind=1)[,1]
        list_elimine_PMR<-which(Rt_diff_PMR>lim_h,arr.ind=1)[,1]
        list_elimine<-c(list_elimine,list_elimine_PMR)
        list_elimine<-list_elimine[-which(duplicated(list_elimine))]
        if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
          Rt_diff<-Rt_diff[-list_elimine,]
          rt_diff<-rt_diff[-list_elimine,]
          Rt_diff_PMR<-Rt_diff_PMR[-list_elimine,]
          rt_diff_PMR<-rt_diff_PMR[-list_elimine,]
          PMR_diff<-PMR_diff[-list_elimine,]
        }
        
        # limite basse
        list_elimine<-which(Rt_diff<lim_b,arr.ind=1)[,1]
        list_elimine_PMR<-which(Rt_diff_PMR<lim_b,arr.ind=1)[,1]
        list_elimine<-c(list_elimine,list_elimine_PMR)  
        list_elimine<-list_elimine[-which(duplicated(list_elimine))]
        if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
          Rt_diff<-Rt_diff[-list_elimine,]
          rt_diff<-rt_diff[-list_elimine,]
          Rt_diff_PMR<-Rt_diff_PMR[-list_elimine,]
          rt_diff_PMR<-rt_diff_PMR[-list_elimine,]
          PMR_diff<-PMR_diff[-list_elimine,]
        }
      }
      Rt<-rbind(Rt,Rt_diff)
      Rt_PMR<-rbind(Rt_PMR,Rt_diff_PMR)
      rt<-rbind(rt,rt_diff)
      rt_PMR<-rbind(rt_PMR,rt_diff_PMR)
      PMR<-rbind(PMR,PMR_diff)
      
      N_exp<-as.numeric(dim(Rt)[1])
      diff_N<-ceiling((N-N_exp)/2)*2
    } # fin du while retirage des scénarios hors scope
  } # fin du si()else sur la limite de retirage
  if (dim(Rt)[1]>N) {
    Rt<-Rt[1:N,]
    Rt_PMR<-Rt_PMR[1:N,] 
    rt<-rt[1:N,]
    rt_PMR<-rt_PMR[1:N,]
    PMR<-PMR[1:N,]
  }
  

  ##########################################################
  # calcul du deflateur sur base pas_discr##################
  ##########################################################
    # Formation des déflateurs à partir des taux sans risques continu
  #Calcul du déflateur pour toutes les périodes de projection en taux continus
  Defl2<-exp(-Rdtcumul(Rt))
  # deflateur avec PMR
  Defl2_PMR<-exp(-Rdtcumul(Rt_PMR))  
  print("fin de calcul des deflateurs")
  flush.console()
  #########################################################
  # Remise sur base de temps pas_t   ######################
  #########################################################
  # slicing Rt et Defl sur base pas_t
  nb_pas<-Tf/pas_t
  #RdtDefl<-matrix(0,nrow=N,ncol=nb_pas)
  RdtDefl<-Defl2[,seq(1,dim(Rt)[2],pas_t/pas_discr)]
  # savegarde au format Rdata de la matrice des déflateurs
  save(RdtDefl, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie_defl,".Rda",sep=""))
  
  # avec PMR
  RdtDefl<-Defl2_PMR[,seq(1,dim(Rt)[2],pas_t/pas_discr)]
  # savegarde au format Rdata de la matrice des déflateurs
  save(RdtDefl, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie_defl,"_PMR.Rda",sep=""))
  rm(Defl2,RdtDefl);gc()
  # recalcul sur pas_t des Rt_PMR et sauvegarde
  Rt2<-matrix(0,nrow=N,ncol=nb_pas)
  # Rt_PMR<-Rdtcumul(Rt_PMR,pas_t/pas_discr)/(pas_t/pas_discr) # fonction qui calcule la moyenne glissante
  Rt2<-Rt_PMR[,seq(1,dim(Rt_PMR)[2],pas_t/pas_discr)]
  Rt2<-Rdtcumul(Rt2,pas_t/pas_discr)
  Rt_PMR<-matrix(0,nrow=N,ncol=nb_pas)
  Rt_PMR<-Rt2
  save(Rt_PMR, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie_Rt,"_PMR.Rda",sep=""))
  
  # recalcul sur pas_t des Rt et sauvegarde
  Rt2<-matrix(0,nrow=N,ncol=nb_pas)
  Rt<-Rdtcumul(Rt,pas_t/pas_discr) # fonction qui calcule la moyenne glissante
  Rt2<-Rt[,seq(1,dim(Rt)[2],pas_t/pas_discr)]
  Rt<-matrix(0,nrow=N,ncol=nb_pas)
  Rt<-Rt2
  save(Rt, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie_Rt,".Rda",sep=""))
  rt2<-matrix(0,nrow=N,ncol=nb_pas)
  rt2<-rt[,seq(1,dim(rt)[2],pas_t/pas_discr)]
  rt<-rt2
  save(rt, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/","rt.Rda",sep=""))
  
  # remise de PMR au pas_t
  rt2<-PMR[,seq(1,dim(PMR)[2],pas_t/pas_discr)]
  PMR<-rt2
  save(PMR,file=paste(reptravail,"/R2 CUBE/R2 IN/PMR.Rda" ,sep=""))
  
  rm(Rt2,rt2,Rt_PMR,rt_PMR);gc()
  # recalcul de f0t au pas_t
  Calib_Tauxf0(Param_EIOPA,reptravail,pas_t,sc)
  load(paste(reptravail,"/R4 CALIBRAGE/R4 OUT/f0t_liss_",sc,".Rda",sep=""))
  f0t_interp<-t(f0t_liss)
  f0t_interp<- f0t_interp[(1:nb_pas)]
  # sauvegarde de f0t et P0t
  # fait ds la fonction appelée du calcul de f0

  print(paste("calcul des aléa equiv sur base ",pas_t,sep=""))
  flush.console()
  
  # calcul inverse des epsilons (residus à correler) de Rt
  Mat_resid_Rt<-array(0,dim=c(N,nb_pas))

  for (i in 1:(nb_pas-1)){
    Mat_resid_Rt[,i+1]<-(rt[,(i+1)]-(rt[,i]*exp(-a*pas_t)+f0t_liss[i+1]-f0t_liss[i]*exp(-a*pas_t)+sigma^2/2*(K((i+1)*pas_t,a)^2-exp(-a*pas_t)*K(i*pas_t,a)^2)))/L(pas_t,sigma,a)^0.5
  }
  
  print(paste("fin de calcul de Rt sur base ",pas_t,sep=""))
  flush.console()
 
  # mean(apply(Mat_resid_Rt,2,mean))
  # mean(apply(Mat_resid_Rt,2,sd))
  
  # calcul d'epsilon, matrice des brownien correlés
  #################################################
  print("génération du cube des variables alétoires corrélées centrées réduites")
  flush.console()
  
  cubealea(Mat_resid_Rt,N,Tf,nom_corr_csv,nom_sortie_cubealea,pas_t)
  
  print("fin de calcul du cube des aléatoires et enregistrement")
  flush.console()  
  
  #libere la mémoire vive inutile
  #rm(list=c('Rt','a','a1','a2','a3','sigma','RdtDefl','CumulTrSR','Rt2','Defl2','t','Mat_resid'))
  rm(list=ls())
  gc()
  
} #fin fonction
  
