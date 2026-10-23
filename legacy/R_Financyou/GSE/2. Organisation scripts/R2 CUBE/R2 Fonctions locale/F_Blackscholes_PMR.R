# La fonction suivante simule NS de rendement distribué selon un processus MBG

Blackscholes_PMR<-function(mu,sigma,Norm,t,PMR){
x<-(mu-sigma^2/2+PMR*sigma)*t+sigma*(t^0.5)*Norm
x
}
