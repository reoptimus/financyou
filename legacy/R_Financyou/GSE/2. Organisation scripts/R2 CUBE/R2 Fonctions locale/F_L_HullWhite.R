## Fonction L du modèle Hull White

L <- function(t,sigma,k){
  y <- sigma^2/(2*k)*(1-exp(-2*k*t))
  return(y)
}
