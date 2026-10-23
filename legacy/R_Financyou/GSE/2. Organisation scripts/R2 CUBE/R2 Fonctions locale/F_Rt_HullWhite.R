# Fonction générant un pas de temps taux court annuel de Hull-White (pas de fonctions de comptage du temps complexe) 

Rt_HW <- function(t,rt,k,vol,f0,epsilon,pas_t)
{
  # calcul
  # t est ici un increment et non un temps!
  a1 <- rt*exp(-k*pas_t)+f0[t+1]-f0[t]*exp(-k*pas_t)
  a2 <- vol^2/2*(K((t)*pas_t,k)^2-exp(-k*pas_t)*K((t-1)*pas_t,k)^2)
  a3 <- sqrt(L(pas_t,vol,k))*epsilon
  # résultats
rslt<-a1+a2+a3
return(rslt)
}