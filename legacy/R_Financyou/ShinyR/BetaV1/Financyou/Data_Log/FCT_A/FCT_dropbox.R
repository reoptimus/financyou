
outputDir <- "FinancYou_data"
nom_data<-"BDD.Rda"

saveData <- function(to_outputDir,nom_data) {
  filepath<-paste0("./Data_Log/",nom_data)
  drop_upload(filepath,path=to_outputDir)
}

loadData <- function(from_outputDir,nom_data) {
  filePaths <- paste0(from_outputDir,"/")
  drop_download(path=paste0(filePaths,nom_data),local_path = paste0("./Data_Log/",nom_data),overwrite=TRUE)
}