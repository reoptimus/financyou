############################
#Fct: calcule de r*
#
############################
# recherche du zero de la fonction:
#  sum(c*a*exp(-k*r))-1 = 0
#
# c, a et k sont des vecteurs t0,...,tn
#reptravail<-'\\\\intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts/R4 CALIBRAGE/R4 Commande locale'
#source(paste(reptravail,"/Uniroot_r.R",sep=""))

Uniroot_r<-function(c,b,k,r){
  nb_pas<-length(b)
  f<-0
  for (i in 1:nb_pas){
  f<-c[i]*b[i]*exp(-k[i]*r)+f
  }
  f<-f-1
  f
}

#plot(c(-10:10),f(a,k,c(-10:10)))
#sapply(r,function(x)
#  uniroot(Uniroot_r,a=a,k=k, interval=c(-10,10),tol=0.001,extendInt="yes")$root