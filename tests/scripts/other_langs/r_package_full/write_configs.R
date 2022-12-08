library(jsonlite)

args <- commandArgs(trailingOnly=TRUE)

trial_dir <- args[1]
param_path <- file.path(trial_dir, "parameters.json")
data <- read_json(path=param_path)

x0 <- data$x0
x1 <- data$x1
x2 <- data$x2
x3 <- data$x3
x4 <- data$x4
x5 <- data$x5

X <- c(x0, x1, x2, x3, x4, x5)

df <- data.frame(X)

write.csv(df, file.path(trial_dir, "data.csv"), row.names = FALSE)