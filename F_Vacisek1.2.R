# La fonction suivante  simule NS valeur It+1 sachant It (distribué selon le processus de Vacisek1)

Vacisek1<-function(It,Force,Moyenne,Volatilite,Norm){
  #formule modifier pour calculer le rendement de t à t+1 (et non le rendement depuis t0)
ItPlus1=It*(exp(-Force))+Moyenne*(1-exp(-Force))+sqrt((1-exp(-2*Force))/(2*Force))*Volatilite*Norm
ItPlus1
}

