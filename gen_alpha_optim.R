#################
#
# fonction pour calculer les soltot automatiquement
#
# pour plusieurs parametres
#
# en recalculant GSE++
# script de constitution des optimum soltot
# en vue de l'approximation

library(devtools)
library(MASS)

reptravail<-paste0("D:/","R_Financyou")
pas_t<-0.5 # pas de temps de la diffusion du cube
D<-30 #(Tp-1) #duree de l'investissement
horiz<-20
numerotation<-"20200820"

###################
#
# Recalcul du GSE ++
# Investmoy<-200000 #investissement moyen retenue
# Net_imposable<-80000
# numerotation<-"20200114"
source(paste0(reptravail,"/GSE+/Formation_GSE++.R"))
source(paste0(reptravail,"/MOCA/FCT/Script_Bootstrap_V5_quick.R"))

# dim(GSEpp_an) == dim(GSE_plac_taxes_an)
Aversion=c(0.5,5,50)
Nbboots<-30

##### generation de la table des contraintes
pavage<-9
interv<-round(1/(pavage-1),1)
list_pavage<-sort(c(0.0001,seq(0,0.8,interv)))
nb_pavage<-length(list_pavage)

# pavage^4*length(Aversion)
Tr_imp<-c(0,0.14,0.3,0.41,0.45)
Investmoy<-200000 # considere faiblement sensible: a confirmer

# definition de la liste des placements elementaires
load(file=paste0(reptravail,"/GSE+/R1 CUBE++/R1 OUT/","GSE++_",numerotation,".Rda"))
rm(GSE_plac_taxes_an,GSE_plac_taxes_cuml)
gc()
# list_placements
num_placements<-seq(1:length(list_placements))
List_retrait<-c(2,3,4,5,6)
list_placements_compl<-list_placements[-List_retrait]
num_placements_compl<-num_placements[-List_retrait]

List_alpha_approx<-as.data.frame(array(0,dim=c(pavage^4*length(Aversion)*length(Tr_imp),8)))
Tab_alpha_approx<-array(0,dim=c(length(list_placements_compl),horiz,pavage^4*length(Aversion)*length(Tr_imp)))
# dim(Tab_alpha_approx)
colnames(List_alpha_approx)<-c("num","GSE","Apetence","Nbboots","ImmoPropre","crd_ImmoPropre","Pinel","crd_Pinel")

int<-1
o<-1
for (o in 1:length(Tr_imp)) { # boucle sur les GSE
Tr_imp_c<-Tr_imp[o]
nom_GSE<-paste0(numerotation,"_",Tr_imp_c)
formation_GSEpp(reptravail,Investmoy,Tr_imp_c,D,pas_t,nom_GSE)

nom_GSE<-paste0("GSE++_",nom_GSE,".Rda")
load(file=paste0(reptravail,"/GSE+/R1 CUBE++/R1 OUT/",nom_GSE))

# retrait des actifs non voulus
GSEpp_an<-GSE_plac_taxes_an[,1:horiz,1:horiz,-List_retrait]

for (ap in 1:length(Aversion)) {
  for (i in 1:nb_pavage){#immopropre
    for (j in 1:nb_pavage) { #crd_immopropre
      for (k in 1:nb_pavage) { #pinel
        for (l in 1:nb_pavage) {#crd_pinel
          if (list_pavage[i]+list_pavage[j]+list_pavage[k]+list_pavage[l] < 1.01) {
            List_alpha_approx<-add_row(List_alpha_approx)
          List_alpha_approx$num[int]<-int
          List_alpha_approx$GSE[int]<-paste0("Tr_imp_",Tr_imp_c)
          List_alpha_approx$Apetence[int]<-Aversion[ap]
          List_alpha_approx$Nbboots[int]<-Nbboots
          List_alpha_approx$ImmoPropre[int]<-list_pavage[i]
          List_alpha_approx$crd_ImmoPropre[int]<-list_pavage[j]
          List_alpha_approx$Pinel[int]<-list_pavage[k]
          List_alpha_approx$crd_Pinel[int]<-list_pavage[l]
          ##### calcul des optimum Marko bootstrap par actifs, D, aversion #############
          tabl_pourc_cont0 <- array(0,dim=c(1,dim(GSEpp_an)[4]))
          tabl_pourc_cont0[which(list_placements_compl=="RimmoPropre")] <- List_alpha_approx$ImmoPropre[int]
          tabl_pourc_cont0[which(list_placements_compl=="crd_RimmoPropre")] <- List_alpha_approx$crd_ImmoPropre[int]
          tabl_pourc_cont0[which(list_placements_compl=="RimmoPinel")] <- List_alpha_approx$Pinel[int]
          tabl_pourc_cont0[which(list_placements_compl=="crd_RimmoPinel")] <- List_alpha_approx$crd_Pinel[int]
          soltot<-Boot_Michaud(GSEpp_an,pas_t,Nbboots,Aversion[ap],tabl_pourc_cont0)
          Tab_alpha_approx[,,int]<-soltot[,]
          # incrementation de int
          print(int)
          int<-int+1
          } # boucle if
        }
      }
    }
  }
}
}
# retrait des zero
List_zero<-which(apply(Tab_alpha_approx[,,],3,sum)==0)
Tab_alpha_approx<-Tab_alpha_approx[,,-List_zero]
List_alpha_approx<-List_alpha_approx[-List_zero,]
List_alpha_approx[1:10,]

# apply(Tab_alpha_approx[,,100],2,sum)
# plot(Tab_alpha_approx[1,,100],type="l",ylim=c(0,1))
# for (i in 2:13) {
# lines(Tab_alpha_approx[i,,100],type="l",col=i)
# }

# which(List_alpha_approx[,2]=="GSE_Netimp_30keur")
save(Tab_alpha_approx,file=paste0(reptravail,"/MOCA/OUT/Tab_alpha_approx_13112020.Rda"))
save(List_alpha_approx,file=paste0(reptravail,"/MOCA/OUT/List_alpha_approx_13112020.Rda"))

list_placements_compl<-list(num_placements_compl,list_placements_compl)
save(list_placements_compl,file=paste0(reptravail,"/MOCA/OUT/List_plc_13112020.Rda"))



