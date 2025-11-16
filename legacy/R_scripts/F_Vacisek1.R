# La fonction suivante  simule NS valeur It+1 sachant It (distribué selon le processus de Vacisek1)

Vacisek1<-function(It,Force,Moyenne,Volatilite,Norm,pt){
ItPlus1=It*exp(-Force*pt)+Moyenne*(1-exp(-Force*pt))+sqrt((1-exp(-2*Force*pt))/(2*Force))*Volatilite*Norm #*(pt)^0.5
ItPlus1
}

