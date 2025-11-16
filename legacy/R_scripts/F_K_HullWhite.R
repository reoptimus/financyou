## Fonction K du modèle Hull White

K <- function(t,k){
  y <- (1-exp(-k*t))/k
  return(y)}