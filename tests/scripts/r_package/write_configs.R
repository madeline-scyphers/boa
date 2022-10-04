library(jsonlite)

args <- commandArgs(trailingOnly=TRUE)

data_path <- args[1]
data <- read_json(path=data_path)
