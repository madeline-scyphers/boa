library(jsonlite)

args <- commandArgs(trailingOnly=TRUE)

data_path <- args[1]
data <- read_json(path=data_path)

trial_dir <- data$trial_dir

x0 <- data$parameters$x0
x1 <- data$parameters$x1
x2 <- data$parameters$x2
x3 <- data$parameters$x3
x4 <- data$parameters$x4
x5 <- data$parameters$x5

X <- c(x0, x1, x2, x3, x4, x5)

df <- data.frame(X)

write.csv(df, file.path(trial_dir, "data.csv"), row.names = FALSE)