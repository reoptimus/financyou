###############
# fct: Calib_Taux_Swaptions_M1
###############
#Script qui optimise les paramètres de HW pour le modèle de taux
#
#
# crée le: 26/06/2018 par Sébastien Gallet
# modifiée le: 10/08/2018 par Sébastien Gallet
#
# Version : 1
#
# variables d entree#######################
# Param_calib_Taux_swaptions = nom du fichier XL des prix des swaptions (enregistre ds "IN")
# reptravail= le chemin du repertoire de travail
# Mat_res = Matrice des residus correlés Epsilon
# nom_sortie = nom donne a la variable de sortie.Rda, ici a et sigma
# pas_t = le pas de temps en année (ex: 0.5 pour 6mois)
###########################################

Calib_Taux_Swaptions_M1 <- function(Prix_swaptions,reptravail,Mat_resid_name,Param_EIOPA,nom_sortie,pas_t)
  {
  library(xlsx)
  library(plot3D)
  library(plot3Drgl)
   
################## initialisation à effacer
pas_t<-0.025
reptravail<-'\\\\intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG_V2/2. Organisation scripts/'
Prix_swaptions<-"Prix_swaptions_bloomberg.Rda" #nom variable: PS_Norm_mat
Mat_resid_name<-'Epsilon.Rda'
Param_EIOPA<-"EIOPA_avril_2018_FRANCE.xlsx" 
# 1er feuille
#col 2:baseline , 3:YCU , 4:YCD , 5:Baseline VA , 6:YCU VA , 7:YCD VA
Rate_curve_nb<-2
# 2ieme feuille
# tableau des choques bonds gouv,corpo et equities

nom_sortie<-"a_sigma"
##################

Mat_EIOPA<-read.xlsx(file=paste(reptravail,"R4 CALIBRAGE/R4 IN/",Param_EIOPA, sep=""),1, header=TRUE)

#chargement de la courbe des taux (EIOPA) et recalcul des courbes f0t et P0t
source(paste(reptravail,"R4 CALIBRAGE/R4 FCT/","Calib_Tauxf0_V1.R",sep=""))

# variables internes (ecrasent la derniere serie de P0t et f0t)
Calib_Tauxf0(Mat_EIOPA[,Rate_curve_nb],reptravail,pas_t)
load(file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/","Prix_P0t_interp",".Rda",sep=""))
load(file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/","f0t_liss",".Rda",sep=""))
####################

#chargement des données des swaptions
load(file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/",Prix_swaptions,sep=""))
nb_swaptions<-length(PS_Norm_mat[1,])-1

# initialisation de r0#####
r0<-f0t_liss[1] #a confirmer
###########################

#mise en forme des données###############################
Taux_swaptions<- as.numeric(PS_Norm_mat[5,2:(nb_swaptions+1)])/100 #ATTENTION en bp dans le fichier XL
Strike<-as.numeric(PS_Norm_mat[4,2:(nb_swaptions+1)])
t_jambe<-as.numeric(PS_Norm_mat[3,2:(nb_swaptions+1)])
Maturite<-as.numeric(PS_Norm_mat[1,2:(nb_swaptions+1)])
Tenor<-as.numeric(PS_Norm_mat[2,2:(nb_swaptions+1)])
S<-Maturite+Tenor

#Ponderation<-rev(sort(seq(1,nb_swaptions*10,by=10)))#rep(1,nb_swaptions)
nb_swaptions_considere<-5
Ponderation<-c(rep(1,(nb_swaptions_considere)),rep(0,(nb_swaptions-nb_swaptions_considere)))
#Ponderation<-as.numeric(PS_Norm_mat[6,2:(nb_call+1)]) # ligne des pondérations à ajouter ds PS_Norm_mat
########################################################

#chargement des fonctions de calcul du prix des swaptions
source(paste(reptravail,"R4 CALIBRAGE/R4 FCT/Prix_swaptions_V1.R",sep="")) #calcul par formules fermées
source(paste(reptravail,"R4 CALIBRAGE/R4 FCT/Prix_swaptions_M2_V2.R",sep="")) #calcul monte carlo
source(paste(reptravail,"R4 CALIBRAGE/R4 Commande locale/Prix_swaption_Normal_Uniroot.R",sep="")) #calcul du prix des swaptions

# initialisation des variables a , sigma , erreur
nb_pas_opt<-5 #nombre de pas de calcul par boucle d'optimisation (la même pour sigma et a) ATTENTION TOUJOURS IMPAIR
deb_a<-0.01 #valeur centrale
pas_a<-deb_a/((nb_pas_opt-1)/2)/1.2
deb_sigma<-0.01 # en %/100
pas_sigma<-deb_sigma/((nb_pas_opt-1)/2)/1.2

# boucle1 sur l'evolution de a,sigma
nb_bcl<-5
res_a_min<-array(0,dim=c((nb_bcl+1),1))
res_sigma_min<-array(0,dim=c((nb_bcl+1),1))
res_a_min[1]<-deb_a
res_sigma_min[1]<-deb_sigma

for (m in 1:nb_bcl) { #nombre d'iteration decidé à l'avance

    #initialisation de la boucle
    a<-seq((deb_a-(nb_pas_opt-1)*pas_a/2),(deb_a+(nb_pas_opt-1)*pas_a/2),pas_a)
    # sigma en bp
    sigma<-seq((deb_sigma-(nb_pas_opt-1)*pas_sigma/2),(deb_sigma+(nb_pas_opt-1)*pas_sigma/2),pas_sigma)
    #on s'assure qu'il n'y ai pas de a ou sigma negatif ou =0 ni sigma>1
    a<-subset(a,a>0)
    sigma<-subset(sigma,sigma>0)
    
    #ecriture matricielle
    # Ma<-t(array(rep(a),dim=c(length(a),length(sigma))))
    # Msigma<-array(rep(sigma),dim=c(length(sigma),length(a)))

    erreur<-array(0,dim=c(length(sigma),length(a),nb_swaptions)) #stockage de la matrice 3D l'erreur par swaption
    erreur_tot<-array(0,dim=c(length(sigma),length(a))) #matrice d'erreur global ponderee sur l'ensemble des swaptions disponibles
    
    MTauxswaptions<-array(0,dim=c(length(sigma),length(a),nb_swaptions))
      # boucle2 sur les différents swaptions disponibles (t,T,n)


      for (i in 1:nb_swaptions) {
        # matrice des tirages aleatoire pour le calcul mar methode MonteCarlo adaptée au temps de chaque swaption
        N<-1000 #dim(Mat_resid) [2]
        nb_pas<-(S[i]/pas_t+1)
        Mat_resid<-array(rnorm(nb_pas*N/2, mean = 0, sd = 1),dim=c(N/2,nb_pas))
        Mat_resid<-rbind(Mat_resid,-Mat_resid) #variables antitetiques

        for (j in 1:length(sigma)){
          for (k in 1:length(a)) {

          # fonction qui pour (t,T,n,a,sigma) renvoie le prix du swaption (à partir de f0, P0(t) )
            #choix du type de formule
          # formule fermee
          # Prixswaptions<-Prix_swaptions_FF(0,Maturite[i],S[i],t_jambe[i],Strike[i],a[k],sigma[j],f0t_liss,r0,P0t_interp,reptravail)
            
          # formule par calcul monte carlo
         
          Prixswaptions<-Prix_swaptions_MC (0,Maturite[i],S[i],t_jambe[i],Strike[i],a[k],sigma[j],f0t_liss,P0t_interp,reptravail,Mat_resid)

          MTauxswaptions[j,k,i]<-uniroot(Prix_swaption_Normal_Uniroot,Ta=Maturite[i],Tb=S[i],n=t_jambe[i],K=Strike[i],P0t=P0t_interp,prixsw=Prixswaptions,pas_P0t=pas_t, interval=c(-10,10),tol=0.0001,extendInt="yes")$root
           
           # à modifier
           # application de la fonction Prix_swaptions à une matrice (voir  apply() ou lapply ou sapply) à finaliser
           # gain important en temps de calcul à attendre
           
            }
        }
        
        erreur[,,i]<-(array(rep(Taux_swaptions[i]),dim=c(length(sigma),length(a)))-MTauxswaptions[,,i])^2 #erreur quadratique en Vol%
      } #fin boucle 2 sur les a et sigma

      gc() #rafraichissement memoire
      
      #calcul de l'erreur (fonction à minimiser)
      Ponderation3D<-array(rep(Ponderation,length(a)*length(sigma)),c(nb_swaptions,length(a),length(sigma)))
      Ponderation3D<-aperm(Ponderation3D,c(3,2,1))
      erreur<-(erreur*Ponderation3D/sum(Ponderation)) #ponderation de l'err quadratique en 3D dim(sigma)*dim(a)*nb_swaptions
      erreur_tot<-apply(erreur,c(1,2),sum) #matrice dim(sigma)*dim(a) des erreurs^2 ponderees des prix swaptions
      erreur_tot<-erreur_tot^0.5
      
      #visualisation
      z<-log(erreur_tot)
      persp3D(x=sigma,y=a,z=z
            ,  smooth = FALSE, lighting = TRUE, new = TRUE,expand = 0.3, theta = -60,phi=20,box = TRUE,
            contour = list(side = c("zmax", "z")), zlim= c(min(z), max(z)),xlab="sigma",ylab="a",zlab="log(err)",
            cex.lab=1,cex.axis=1,ticktype="detailed"
            )

      #test pour connaître la zone de l'amélioration 
      sigma_min<-which(erreur_tot==min(erreur_tot),arr.ind = TRUE)[1]
      a_min<-which(erreur_tot==min(erreur_tot),arr.ind = TRUE)[2]
      #convertion de l'indice en valeur
      sigma_min<-sigma[sigma_min]
      a_min<-a[a_min]
      
      #calcul de la distance entre l'ancien optimum et le nouveau
      gap_sigma<-(sigma_min-deb_sigma)
      gap_a<-(a_min-deb_a)
      #calcul des nouveaux pas de recherche
      pas_a<-max(abs(gap_a)/((nb_pas_opt-1)/2),pas_a/((nb_pas_opt-1)/2))
      pas_sigma<-max(abs(gap_sigma)/((nb_pas_opt-1)/2),pas_sigma/((nb_pas_opt-1)/2)) 
      #reinitialisation de la boucle
      deb_sigma<-sigma_min
      deb_a<-a_min
      #ecriture de point de passage de la convergence
      res_a_min[m+1]<-deb_a
      res_sigma_min[m+1]<-deb_sigma
      print(m)
  } #fin boucle1

a<-res_a_min[nb_bcl]
sigma<-res_sigma_min[nb_bcl]
plot(res_a_min,type="o",
     main=paste("a_min per iteration pour ",sum(ifelse(Ponderation!=0,1,0))," swaptions",sep=""),
     xlab="iteration",ylab="a")

plot(res_sigma_min,type="o",
     main=paste("sigma_min per iteration pour ",sum(ifelse(Ponderation!=0,1,0))," swaptions",sep=""),
     xlab="iteration",ylab="sigma")

#savegarde au format Rdata de (a ,sigma) optimisés
save(a,sigma,f0t_liss, file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/",nom_sortie,".Rda",sep=""))
#load(file=paste(reptravail,"R4 CALIBRAGE/R4 OUT/",nom_sortie,".Rda",sep=""))

#efface les variables utilisées pour les calculs
rm(list=c('MTauxswaptions','erreur','erreur_tot','r0','obj','Msigma','Ma','gap','deb_sigma','deb_a',"Ponderation3D","nb_swaptions","nb_pas_opt","i","j","k","gap_a","gap_sigma","a_min","sigma_min","pas_a","pas_sigma"))
#rm(list=ls())
gc()

} #fin fonction