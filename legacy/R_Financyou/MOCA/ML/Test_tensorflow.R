install.packages("reticulate")
install.packages("tensorflow")

library(reticulate)

library(tensorflow)
Sys.setenv(RETICULATE_PYTHON="C:/Users/Karen et Seb/python/Scripts")
use_python("/usr/local/bin/python")
use_virtualenv("C:/Users/Karen et Seb/python/Lib/site-packages/_virtualenv.py")
use_condaenv("myenv")
install_tensorflow()


library(reticulate)
os <- import("os")
os$listdir(".")