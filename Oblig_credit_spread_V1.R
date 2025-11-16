#Sript de calcul des probabilit? de default et du spread
# a partir des matrice des probabilit? de transtion S&P transition

Oblig_spread <- function(Matur,cube,pas_t,reptravail,RecoBond,RecoCBond)
{
  # library("xlsx")
  # library("abind")
#var genreale utilisee
  # RecoBond<-0.6 #Taux de recouvrement de la dette en cas de default
  # RecoCBond<-0.3
  # reptravail<-getwd()
  # nom_cube<- cube # la variable
  # pas_t<-0.5
  # Matur=10
  
# chargement du cube GSE
# repcube<-paste0(reptravail,"/GSE/2. Organisation scripts")  
# ad_GSE<-"/R1 MEFCUBE/R1 OUT/"
# load(paste0(repcube,ad_GSE,nom_cube))

NS<-dim(cube)[1]
nb_pas<-dim(cube)[2]

#Import spread S&P 
###################
Appel_table="D:/R_Financyou/GSE+/R2 CUBE+/"
load(paste0(Appel_table,"R2 IN/","Bond S&P Matrice transition.csv"))
load(paste0(Appel_table,"R2 IN/","C-Bond S&P Matrice transition.csv"))
Yields_Bond<-as.data.frame(read.xlsx(file=paste0(Appel_table,"R2 IN/","Yields_CBond_20191216.xlsx"),sheetIndex = 1),"Yields"=Numeric(3),stringsAsFactors=FALSE)
NbGrade<-length(CBondTransi0[,1])
Yields_Bond<-Yields_Bond[,2]/100
Yields_CBond<-Yields_Bond+1/100 # plus 2% pour les yields corpo: a dire d'expert

# mise ? l'?quilibre de la matrice de transition (somme des lignes = 1)
BondTransi0<-BondTransi0+array(rep((1-apply(BondTransi0,1,sum))/NbGrade,NbGrade),dim=c(NbGrade,NbGrade))
CBondTransi0<-CBondTransi0+array(rep((1-apply(CBondTransi0,1,sum))/NbGrade,NbGrade),dim=c(NbGrade,NbGrade))

# calcul de la proba de faire defaut avant la maturit?
BondTransi<-BondTransi0
CBondTransi<-CBondTransi0
for(l in 1:(Matur-1) ) {
  #MatDefaultRateB[,l]<-BondTransi[,NbGrade]
  BondTransi<-BondTransi %*% BondTransi0
  
  #MatDefaultRateCB[,l]<-CBondTransi[,NbGrade]
  CBondTransi<-CBondTransi %*% CBondTransi0
}
#apply(CBondTransi,1,sum)

# les Yields Grades doivent ?tre transform?s en prix
# ? t0 on consid?re que l'oblig corpo est emise au pair
# soit coupon = yield (et prix = 1)
# on calcul le prix du oblig RN donnant ce coupon ? t0
#source(file=paste0(reptravail,"/R2 CUBE+/R2 Fonctions locale/F_Rdtcumul.R"))
#load des ZC
ZC<-cube[,,2:(Matur+1)]
coupon_RN<-(1-ZC[,,Matur])/apply(ZC[,,1:Matur],c(1,2),sum)

# calcul des prix RN pour les yields grades
P_RN_grades<-array(0,dim=c(NbGrade,1))
P_RN_gradesC<-array(0,dim=c(NbGrade,1))

for (g in 1:NbGrade) {
  # calcul du prix moyen d'une obligation RN donnant le coupon du grade (= yield au pair) ? t=0
  P_RN_grades[g,1]<-mean(Yields_Bond[g]*apply(ZC[,1,1:Matur],c(1),sum)+ZC[,1,Matur])
  P_RN_gradesC[g,1]<-mean(Yields_CBond[g]*apply(ZC[,1,1:Matur],c(1),sum)+ZC[,1,Matur])
}

# calcul des primes de risk Pi fixe sur t
Pi_grades<-(1/P_RN_grades-1)*(-1)/(BondTransi[,NbGrade]*(1-RecoBond))
Pi_gradesC<-(1/P_RN_gradesC-1)*(-1)/(CBondTransi[,NbGrade]*(1-RecoCBond))

# on fixe la prime de rsk constante pour toutes les notations
 # Pi_grades<-0 # niveau moyensur les notation ? dire d'expert
 # Pi_gradesC<-1.5

# formation de la matrice de rendements de transition d'une notation ? l'autre
# ces rendements sont du au changement de la prime (Pi) dans le mod?le JLT
Mat_Rdt_transi<-array(Pi_grades,dim=c(NbGrade,NbGrade))
Mat_Rdt_transi<-1-Mat_Rdt_transi*(1-RecoBond)*array(BondTransi[,NbGrade],dim=c(NbGrade,NbGrade))
Mat_Rdt_transi<-log(t(Mat_Rdt_transi)/Mat_Rdt_transi)
Mat_Rdt_transi[1:(NbGrade-1),NbGrade]<-log(RecoBond)+Mat_Rdt_transi[1:(NbGrade-1),(NbGrade-1)]
Mat_Rdt_transi[NbGrade,1:NbGrade]<-0

Mat_Rdt_transiC<-array(Pi_gradesC,dim=c(NbGrade,NbGrade))
Mat_Rdt_transiC<-1-Mat_Rdt_transiC*(1-RecoCBond)*CBondTransi[,NbGrade]
Mat_Rdt_transiC<-log(t(Mat_Rdt_transiC)/Mat_Rdt_transiC)
Mat_Rdt_transiC[1:(NbGrade-1),NbGrade]<-log(RecoCBond)+Mat_Rdt_transiC[1:(NbGrade-1),(NbGrade-1)]
Mat_Rdt_transiC[NbGrade,1:NbGrade]<-0

##############################################################
### Calcul pour le souverain de la matrice du spread rendement
cube_trans<-array(0,dim=c(NS,nb_pas,NbGrade)) #ma]trice des grade [depart,arriv?e]

j=1
for (i in 1:NbGrade){ #grade de depart
  cube_trans[,,i]<-i
  
  coef_trans<- which(array(rbinom(NS*nb_pas,1,BondTransi0[i,j]*pas_t),dim=c(NS,nb_pas))==1,arr.ind=TRUE)
  if (length(coef_trans[,1])>0){
    for (k in 1:length(coef_trans[,1])) {
      cube_trans[coef_trans[k,1],coef_trans[k,2],i]<-j 
    }
  }
  
  for (j in 2:NbGrade){ #grade de transition
    if (BondTransi0[i,j]<BondTransi0[i,i]) { #autre que le maintient du grade
      # alors on ecrit systematiquement le resultat
      coef_trans<- which(array(rbinom(NS*nb_pas,1,BondTransi0[i,j]*pas_t),dim=c(NS,nb_pas))==1,arr.ind=TRUE)
      # NB: la probabilit? de transition annuelle est pultipli?e par le pas de temps (approxmation acceptable)
      
     } else { # proba plus frequente -> on ecrit que s'il n'y a pas de transition
      coef_trans_temp<- which(array(rbinom(NS*nb_pas,1,BondTransi0[i,j]*pas_t),dim=c(NS,nb_pas))==1,arr.ind=TRUE)
      coef_trans<-merge(coef_trans_temp,which(cube_trans[,,i]==i,arr.ind=TRUE))
     }
    if (length(coef_trans[,1])>0){
      for (k in 1:length(coef_trans[,1])) {
        cube_trans[coef_trans[k,1],coef_trans[k,2],i]<-j 
      }
    }
  }
}
#cube_trans[1:20,1:15,3]
mat_depart<-array(rep(1:NbGrade,NS,nb_pas),dim=c(NbGrade,NS,nb_pas))
mat_depart<-aperm(mat_depart,c(2,3,1))

cube_rdt_grade<-mat_depart #pour la dimmension
# for (i in 1:dim(mat_depart)[1]){
#   for (j in 1:dim(mat_depart)[2]){
#     for (k in 1:dim(mat_depart)[3]){
#       cube_rdt_grade[i,j,k]<-Mat_Rdt_transi[mat_depart[i,j,k],cube_trans[i,j,k]]
#     }
#   }
# }
compo<-function (a,b) {
  Mat_Rdt_transi[a,b]
}

# calcul sur sur-rendement du au coupon grade
coupon_RN<-array(rep(coupon_RN,NbGrade),dim=c(NS,nb_pas,NbGrade))

surrdt_yield<-array(rep(Yields_Bond,NS*nb_pas),dim=c(NbGrade,NS,nb_pas))
surrdt_yield<-aperm(surrdt_yield,c(2,3,1))
surrdt_yield<-pas_t*log((1+surrdt_yield))#/(1+coupon_RN))

# cube du rendement risk: risk-transition + sur-coupon
cube_rdt_grade<-array(mapply(compo,mat_depart,cube_trans),dim=c(NS,nb_pas,NbGrade))+surrdt_yield

save(cube_rdt_grade,file=paste0(Appel_table,"R2 OUT/","cube_rdt_grade.Rda"))
rm(cube_rdt_grade);rm(mat_depart);rm(cube_trans)
gc()

##############################################################
### Calcul pour le corporate de la matrice du spread rendement
cube_trans<-array(0,dim=c(NS,nb_pas,NbGrade)) #ma]trice des grade [depart,arriv?e]

j=1
for (i in 1:NbGrade){ #grade de depart
  cube_trans[,,i]<-i
  
  coef_trans<- which(array(rbinom(NS*nb_pas,1,CBondTransi0[i,j]*pas_t),dim=c(NS,nb_pas))==1,arr.ind=TRUE)
  if (length(coef_trans[,1])>0){
    for (k in 1:length(coef_trans[,1])) {
      cube_trans[coef_trans[k,1],coef_trans[k,2],i]<-j 
    }
  }
  
  for (j in 2:NbGrade){ #grade de transition
    if (CBondTransi0[i,j]<CBondTransi0[i,i]) { #autre que le maintient du grade
      # alors on ecrit systematiquement le resultat
      coef_trans<- which(array(rbinom(NS*nb_pas,1,CBondTransi0[i,j]*pas_t),dim=c(NS,nb_pas))==1,arr.ind=TRUE)
      
    } else { # proba plus frequente -> on ecrit que s'il n'y a pas de transition
      coef_trans_temp<- which(array(rbinom(NS*nb_pas,1,CBondTransi0[i,j]*pas_t),dim=c(NS,nb_pas))==1,arr.ind=TRUE)
      coef_trans<-merge(coef_trans_temp,which(cube_trans[,,i]==i,arr.ind=TRUE))
    }
    if (length(coef_trans[,1])>0){
      for (k in 1:length(coef_trans[,1])) {
        cube_trans[coef_trans[k,1],coef_trans[k,2],i]<-j 
      }
    }
  }
}
#cube_trans[1:20,1:15,3]
mat_depart<-array(rep(1:NbGrade,NS,nb_pas),dim=c(NbGrade,NS,nb_pas))
mat_depart<-aperm(mat_depart,c(2,3,1))

cube_rdt_gradeC<-mat_depart #pour la dimmension
# for (i in 1:dim(mat_depart)[1]){
#   for (j in 1:dim(mat_depart)[2]){
#     for (k in 1:dim(mat_depart)[3]){
#       cube_rdt_gradeC[i,j,k]<-Mat_Rdt_transiC[mat_depart[i,j,k],cube_trans[i,j,k]]
#     }
#   }
# }
compoC<-function (a,b) {
  Mat_Rdt_transiC[a,b]
}

# calcul sur sur-rendement du au coupon grade
surrdt_yieldC<-array(rep(Yields_CBond,NS*nb_pas),dim=c(NbGrade,NS,nb_pas))
surrdt_yieldC<-aperm(surrdt_yieldC,c(2,3,1))
surrdt_yieldC<-pas_t*log((1+surrdt_yieldC))#/(1+coupon_RN))

# cube du rendement risk: risk-transition + sur-coupon
cube_rdt_gradeC<-array(mapply(compoC,mat_depart,cube_trans),dim=c(NS,nb_pas,NbGrade))+surrdt_yieldC

save(cube_rdt_gradeC,file=paste0(Appel_table,"R2 OUT/","cube_rdt_gradeC.Rda"))

#########################################################
#nettoyage des variables non externes
rm(list=ls())
gc()

} # fin de la fonction
# 
# save(CBondTransi0,file=paste0(Appel_table,"C-Bond S&P Matrice transition.csv"))

