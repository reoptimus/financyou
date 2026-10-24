# La fonction suivante  simule NS valeur It+1 sachant It (distribué selon le processus de Vacisek1)

Vacisek1<-function(NS,It,Force,Moyenne,Volatilite,Norm){
ItPlus1=It*exp(-Force)+Moyenne*(1-exp(-Force))+sqrt((1-exp(-2*Force))/(2*Force))*Volatilite*Norm
ItPlus1
}

