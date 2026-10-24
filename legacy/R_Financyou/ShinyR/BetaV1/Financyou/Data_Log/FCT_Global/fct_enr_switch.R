enr_switch<- function (hist_,type,level) {
  if (type=="trend") {
    hist_$avers[[1]]$anticip<-level
  } else {
    if (type=="risk") {
      hist_$avers[[1]]$profilRisk<-level
    } else {}
  }

  return(hist_)
}