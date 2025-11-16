# La fonction suivante simule NS de rendement distribué selon un processus MBG

Blackscholes<-function(mu,sigma,Norm,t){
x<-(mu-sigma*sigma/2)*t+sigma*(t^0.5)*Norm
x
}
