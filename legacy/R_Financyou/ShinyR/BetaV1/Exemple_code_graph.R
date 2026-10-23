plot.stacked <- function(x,y, ylab="", xlab="", ncol=1, xlim=range(x, na.rm=T), ylim=c(0, 1.2*max(rowSums(y), na.rm=T)), border = NULL, col=rainbow(length(y[1,]))){
  
  plot(x,y[,1], ylab=ylab, xlab=xlab, ylim=ylim, xaxs="i", yaxs="i", xlim=xlim, t="n")
  bottom=0*y[,1]
  for(i in 1:length(y[1,])){
    top=rowSums(as.matrix(y[,1:i]))
    polygon(c(x, rev(x)), c(top, rev(bottom)), border=border, col=col[i])
    bottom=top
  }
  abline(h=seq(0,200000, 10000), lty=3, col="grey")
  legend("topright", rev(colnames(y)), ncol=ncol, inset = 0, fill=rev(col), bty="0", bg="white", cex=0.8, col=col)
  box()
}

x<-seq(50)
y<-array(0,dim=c(50,3))
colnames(y)<-c("A","B","C")
y<-as.data.frame(y)
y$A<-0.1*x+0
y$B<-0.1*x-0.5
y$C<--0.1*x+5
plot.stacked(x,y)
#####################################################
set.seed(1)
m <- 500
n <- 15
x <- seq(m)
y <- matrix(0, nrow=m, ncol=n)
colnames(y) <- seq(n)
for(i in seq(ncol(y))){
  mu <- runif(1, min=0.25*m, max=0.75*m)
  SD <- runif(1, min=5, max=30)
  TMP <- rnorm(1000, mean=mu, sd=SD)
  HIST <- hist(TMP, breaks=c(0,x), plot=FALSE)
  fit <- smooth.spline(HIST$counts ~ HIST$mids)
  y[,i] <- fit$y
}

plot.stacked(x,y)

#####################################################

set.seed(1)
m <- 500
n <- 50
x <- seq(m)
y <- matrix(0, nrow=m, ncol=n)
colnames(y) <- seq(n)
for(i in seq(ncol(y))){
  mu <- runif(1, min=0.25*m, max=0.75*m)
  SD <- runif(1, min=5, max=30)
  TMP <- rnorm(1000, mean=mu, sd=SD)
  HIST <- hist(TMP, breaks=c(0,x), plot=FALSE)
  fit <- smooth.spline(HIST$counts ~ HIST$mids)
  y[,i] <- fit$y
}
y <- replace(y, y<0.01, 0)

#order by when 1st value occurs
ord <- order(apply(y, 2, function(r) min(which(r>0))))
y2 <- y[, ord]
COLS <- rainbow(ncol(y2))

par(mar=c(0,0,0,0), bty="n")
plot.stream(x,y2, axes=FALSE, xlim=c(100, 400), xaxs="i", center=TRUE, spar=0.2, frac.rand=0.1, col=COLS, border=1, lwd=0.1)
y <- y[, unique(apply(y, 1, which.max))]

## Use plot.stacked() from Marc's post
plot.stacked(x,y)
#####################################################
y <- y[, unique(apply(y, 1, which.max))]

## Use plot.stacked() from Marc's post
plot.stacked(x,y)

#####################################################
library(ggTimeSeries)
library(ggplot2)

set.seed(10)
dfData = data.frame(
  Time = 1:1000,
  Signal = abs(
    c(
      cumsum(rnorm(1000, 0, 3)), 
      cumsum(rnorm(1000, 0, 4)), 
      cumsum(rnorm(1000, 0, 1)),
      cumsum(rnorm(1000, 0, 2))
    )
  ),
  VariableLabel = c(rep('Class A', 1000),
                    rep('Class B', 1000),
                    rep('Class C', 1000),
                    rep('Class D', 1000))
)

# base plot
ggplot(dfData,
       aes(x = Time,
           y = Signal,
           group = VariableLabel,
           fill = VariableLabel)) +
  stat_steamgraph() +
  theme_bw()