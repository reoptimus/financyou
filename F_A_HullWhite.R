## Fonction A du modèle Hull White

A <- function(tA,TfA,aA,sigmaA,P0tA,fA,nA){
  y <- P0tA[TfA/nA+1]/P0tA[tA/nA+1]*exp(K(TfA-tA,aA)*fA[tA/nA+1]-L(tA,sigmaA,aA)*(K(TfA-tA,aA)^2)/2)
  return(y)
}
