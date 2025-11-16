###############
# fct: HullWhite
###############
#fonction qui genere les taux courts de la formule d'Hull-White, le deflateur et le cube des browniens correlés
#servant de base aux autres calculs (Immo/action)
#à partir des paramètres calibrés
#
# crée le: 7/12/2017 par Fabrice Borel-Mathurin
# modifiée le: 20/12/2019 par Sebastien G.
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
HullWhite <- function(param_calib , Param_EIOPA , sc , nom_corr_csv , nom_sortie_Rt , nom_sortie_defl , nom_sortie_cubealea , N,Tf,pas_t,pas_discr,reptravail,lim_h,lim_b)
{
  
  # Paramètres figés pour démonstration
  # setwd("E:/")
  # reptravail<-getwd()
  # reptravail<-paste0(reptravail,"R_Financyou/GSE/2. Organisation scripts")
  # param_calib<-"a_sigma.Rda"
  # nom_sortie_Rt<-"Tr-Rt"
  # nom_sortie_defl<-"Tr-deflator"
  # N=500
  # Tf=60
  # pas_discr<-0.0025
  # pas_t<-0.5
  # Param_EIOPA<-"EIOPA_avril_2018_FRANCE.xlsx"
  # nom_corr_csv="Corr_ResidAhlgrim_V2.xlsx"
  # nom_sortie_cubealea="Epsilon.Rda"
  # lim_h=0.1
  # lim_b=-0.05
  # sc= 2 #donnée EIOPA baseline

  # Chargement des fonctions utilisées
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rt_HullWhite.R",sep=""))
  source(paste(reptravail,"/R3 CUBE ALEA/R3 FCT/cubealea_V5.R",sep=''))
  # Chargement des fonctions utilisées L() et K()
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_K_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_L_HullWhite.R",sep=""))
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rt_HullWhite.R",sep=""))
  
  #chargement des parametres H&W a et sigma
  load(paste(reptravail,"/R2 CUBE/R2 IN/",param_calib, sep="") )

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

  ###############################################
  #Simulations du taux court Rt  pour toutes les périodes de projection
  ###############################################
  #Initialisation 
  Rt<-matrix(0,nrow=N,ncol=nb_pas)
  rt<-matrix(f0t_liss[1],nrow=N,ncol=nb_pas)
  Tp<-pas_discr
  tp<-0
  
  for(i in 1:(nb_pas-1)){
    #tirage des residus aleatoire
    Mat_resid<-rnorm(N/2,0,1)
    Mat_resid<-c(Mat_resid,-Mat_resid)
    rt[,i+1]<-rt[,i]*exp(-a*pas_discr)+f0t_liss[i+1]-f0t_liss[i]*exp(-a*pas_discr)+sigma^2/2*(K(Tp,a)^2-exp(-a*pas_discr)*K(tp,a)^2)+L(pas_discr,sigma,a)^0.5*Mat_resid
    Rt[,i+1]<-(-log(P0t_interp[i+1]/P0t_interp[i]))+K(pas_discr,a)^2/2*L(tp,sigma,a)-K(pas_discr,a)*(f0t_liss[i]-rt[,i])
   
    Tp<-Tp+pas_discr
    tp<-tp+pas_discr
  }
  print("fin de calcul de Rt")
  flush.console()
  
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
  list_elimine<-list_elimine[-which(duplicated(list_elimine))] #liste sans doublons
  if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
    Rt<-Rt[-list_elimine,]
    rt<-rt[-list_elimine,]
  }
  
  # limite basse
  list_elimine<-which(Rt<lim_b,arr.ind=1)[,1] # numero des lignes < limite basse
  list_elimine<-list_elimine[-which(duplicated(list_elimine))] #liste sans doublons
  if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
    Rt<-Rt[-list_elimine,]
    rt<-rt[-list_elimine,]
  }
  #dim(Rt)
  
  N_exp<-as.numeric(dim(Rt)[1])
  diff_N<-ceiling((N-N_exp)/2)*2
  print(paste("% de scénario retirés: ",diff_N/N,sep=""))
  flush.console()
  
  if (diff_N>N/2) { 
    print(paste("% de scénario à retirer > 50% du tirage initial: ",diff_N/N," -> annulation du filtre",sep=""))
    flush.console()
    }
  else {
    while (diff_N>0) {
      Rt_diff<-matrix(0,nrow=diff_N,ncol=nb_pas)
      rt_diff<-matrix(f0t_liss[1],nrow=diff_N,ncol=nb_pas)
      Tp<-pas_discr
      tp<-0
      

      for(i in 1:(nb_pas-1)){
        #tirage des residus aleatoire
        Mat_resid<-rnorm(diff_N/2,0,1)
        Mat_resid<-c(Mat_resid,-Mat_resid)
        
        rt_diff[,i+1]<-rt_diff[,i]*exp(-a*pas_discr)+f0t_liss[i+1]-f0t_liss[i]*exp(-a*pas_discr)+sigma^2/2*(K(Tp,a)^2-exp(-a*pas_discr)*K(tp,a)^2)+L(pas_discr,sigma,a)^0.5*Mat_resid
        Rt_diff[,i+1]<-(-log(P0t_interp[i+1]/P0t_interp[i]))+K(pas_discr,a)^2/2*L(tp,sigma,a)-K(pas_discr,a)*(f0t_liss[i]-rt_diff[,i])
        
        Tp<-Tp+pas_discr
        tp<-tp+pas_discr
      }
   
      if (is.na(mean(which(Rt_diff>lim_h,arr.ind=1)[,1])) | is.na(mean(which(Rt_diff<lim_b,arr.ind=1)[,1]))) {
      }else {
        # limite haute
        list_elimine<-which(Rt_diff>lim_h,arr.ind=1)[,1]
        list_elimine<-list_elimine[-which(duplicated(list_elimine))]
        if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
          Rt_diff<-Rt_diff[-list_elimine,]
          rt<-rt[-list_elimine,]
        }
        
        # limite basse
        list_elimine<-which(Rt_diff<lim_b,arr.ind=1)[,1]
        list_elimine<-list_elimine[-which(duplicated(list_elimine))]
        if (is.integer(list_elimine) && length(list_elimine) == 0){}else{ #test si liste vide
          Rt_diff<-Rt_diff[-list_elimine,]
          rt<-rt[-list_elimine,]
        }
      }
      Rt<-rbind(Rt,Rt_diff)
      rt<-rbind(rt,rt_diff)
      
      N_exp<-as.numeric(dim(Rt)[1])
      diff_N<-ceiling((N-N_exp)/2)*2
    } # fin du while retirage des scénarios hors scope
  } # fin du si()else sur la limite de retirage
  
  if (dim(Rt)[1]>N) {
    Rt<-Rt[1:N,] 
    rt<-rt[1:N,] 
  }
  
  ##########################################################
  # calcul du deflateur sur base pas_discr##################
  ##########################################################
  # Chargement des fonctions utilisées: cumul des rendements
  source(paste(reptravail,"/R2 CUBE/R2 Fonctions locale/F_Rdtcumul.R",sep=""))
  # Formation des déflateurs à partir des taux sans risques continu
  CumulTrSR<-matrix(0,nrow=N,ncol=nb_pas)
  CumulTrSR<-Rdtcumul(Rt)
  #Calcul du déflateur pour toutes les périodes de projection en taux continus
  Defl2<-exp(-CumulTrSR)
  print("fin de calcul des deflateurs")
  flush.console()
  #########################################################
  # Remise sur base de temps pas_t   ######################
  #########################################################
  # slicing Rt et Defl sur base pas_t
  nb_pas<-Tf/pas_t
  
  RdtDefl<-matrix(0,nrow=N,ncol=nb_pas)
  RdtDefl<-Defl2[,seq(1,dim(Rt)[2],pas_t/pas_discr)]
  # savegarde au format Rdata de la matrice des déflateurs
  save(RdtDefl, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie_defl,".Rda",sep=""))
  rm(RdtDefl);gc()
  
  Rt2<-matrix(0,nrow=N,ncol=nb_pas)
  Rt<-Rdtcumul(Rt,pas_t/pas_discr)#/(pas_t/pas_discr) # fonction qui calcule la somme cumulée glissante
  Rt2<-Rt[,seq(1,dim(Rt)[2],pas_t/pas_discr)]
  #Rt<-matrix(0,nrow=N,ncol=nb_pas)
  Rt<-Rt2
  # savegarde au format Rdata des taux sans risques Rt correles dans le dossier "IN"
  save(Rt, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/",nom_sortie_Rt,".Rda",sep=""))
  
  rt2<-matrix(0,nrow=N,ncol=nb_pas)
  rt2<-rt[,seq(1,dim(rt)[2],pas_t/pas_discr)]
  rt<-rt2
  save(rt, file=paste(reptravail,"/R1 MEFCUBE/R1 IN/","rt.Rda",sep=""))

  # recalcul de f0t au pas_t
  Calib_Tauxf0(Param_EIOPA,reptravail,pas_t,sc)
  load(paste(reptravail,"/R4 CALIBRAGE/R4 OUT/f0t_liss_",sc,".Rda",sep=""))
  f0t_interp<-t(f0t_liss)
  f0t_interp<- f0t_interp[(1:nb_pas)]

  print(paste("calcul des aléa equiv sur base ",pas_t,sep=""))
  flush.console()
  
  # calcul inverse des epsilons (residus à correler) de Rt
  Mat_resid_Rt<-array(0,dim=c(N,nb_pas))
  
  for (i in 1:(nb_pas-1)){
    # a1 <- Rt[,t]*exp(-a*pas_t)+f0t_interp[t+1]-f0t_interp[t]*exp(-a*pas_t)
    # a2 <- sigma^2/2*(K(t*pas_t,a)^2-exp(-a*pas_t)*K((t-1)*pas_t,a)^2)
    # a3 <- sqrt(L(pas_t,sigma,a))
    # Mat_resid_Rt[,t]<-(Rt[,t+1]-a1-a2)/a3
    
    Mat_resid_Rt[,i+1]<-(rt[,i+1]-(rt[,i]*exp(-a*pas_t)+f0t_liss[i+1]-f0t_liss[i]*exp(-a*pas_t)+sigma^2/2*(K(Tp,a)^2-exp(-a*pas_t)*K(tp,a)^2)))/L(pas_t,sigma,a)^0.5
    #Rt[,i+1]<-(-log(P0t_interp[i+1]/P0t_interp[i]))+K(pas_discr,a)^2/2*L(tp,sigma,a)-K(pas_discr,a)*(f0t_liss[i+1]-rt[,i+1])
    
  }

  print(paste("fin de calcul de Rt sur base ",pas_t,sep=""))
  flush.console()
 
  # mean(apply(Mat_resid_Rt,1,mean))
  # mean(apply(Mat_resid_Rt,1,sd))

  # calcul d'epsilon, matrice des brownien correlés
  #################################################
  print("génération du cube des variables alétoires corrélées centrées réduites")
  flush.console()
  
  cubealea(Mat_resid_Rt,N,Tf,nom_corr_csv,nom_sortie_cubealea,pas_t)
  
  print("fin de calcul du cube des aléatoires et enregistrement")
  flush.console()  
  
  #libere la mémoire vive inutile
  rm(list=ls())
  gc()
  
} #fin fonction
  
