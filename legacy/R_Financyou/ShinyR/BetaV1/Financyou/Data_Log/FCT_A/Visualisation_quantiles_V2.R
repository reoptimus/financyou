#################################################
# script pour la visualisation des sorties GSE
# fait le 21/12/2019
# modifie le 06/02/2020
# methode ggplot/geom_polygon/ggsave
#################################################

Visu_quant<- function (tranche,noms_list,sum_epar) {

  # tranche<-apply(Rdt_liquide,c(1,3),sum)
  # noms_list<-list_placements
  # sum_epar<-t(apply(Mat_result,2,sum))
  
# params
N<-dim(tranche[,])[1]
Tmp<-dim(tranche[,])[2]
x<-1:Tmp
# max<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.997)
min<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.01)
# qet2max<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.954)
qet2min<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.10)
# qetmax<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.683)
qetmin<-apply(tranche,MARGIN=2,FUN=quantile,probs=0.5)
 # mean <- apply(tranche,MARGIN=2,FUN=mean)

# trac? non-cumul? str(mean) str(sum_epar[1,])

a<-cbind(min,qet2min,qetmin,sum_epar[1,])
colnames(a)<-c("1%","10%","50%","somme épargnée")
a<-as.data.frame(a,strings2factor=FALSE)

a<-gather(a,key="Pourc")
a$an<-rep(seq(horiz),length(unique(a[,"Pourc"])) )
# changement de l'unite
a$value<-round(abs(a$value/1000),1) # en k eur
a$Pourc<-factor(a$Pourc,levels=c("50%", "10%", "1%","somme épargnée"))
linetype = c("solid", "longdash", "dashed", "dotted")
b<-a%>%filter(Pourc!="somme épargnée")
c<-a%>%filter(Pourc=="somme épargnée")

p<- ggplot() + 
  # geom_area(alpha=0.6 , size=1, colour="black") +
  # theme_ipsum() +
  # scale_fill_viridis(discrete = T,option="C") +
  geom_line(aes(x=b$an,y=b$value,color=b$Pourc) , show.legend = FALSE,
            size=1) +
  scale_color_brewer (palette="Paired") + # "PuBuGn" "Blues"
  theme_light() + # dark , minimal , void , light , classic , bw
  labs(x="Annees de projections",y="Capital \n en milliers Eur",title="", subtitle="",caption="FinancYou.com") +
  theme (legend.position = "right") + # left, right,top legend.background = "black",
   # "solid", "longdash", "dashed", "dotted"
  geom_line(aes(x=c$an,y=c$value,color=c$Pourc),linetype="dotted",size=0.7, show.legend = FALSE)
  # geom_line(key_glyph = "timeseries")

p <- ggplotly(p,tooltip = c("y", "x", "colour"))

return(p)

#lines(x,mean,type="l",col="red")

} #fin de la fonction
