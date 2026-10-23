#chemin<-"//intra/partages/UA2771_Data/3_ST_top-down/3.2_En/6. ESG/2. Organisation scripts/R4 CALIBRAGE/R4 IN/"
#param_action<-read.csv(paste(chemin,"action_param.txt",sep=""),sep=";",header=FALSE)


mu<-0.05
sigma<-0.3
dvd<-0.02
Actiont<-0.03

save(mu,sigma,dvd,Actiont,file="param_action.Rda")

rm(list=c('mu','sigma','dvd','Actiont'))
gc()