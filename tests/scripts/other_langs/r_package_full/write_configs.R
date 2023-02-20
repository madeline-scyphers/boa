# load in any libraries and modules we need
library(jsonlite)

# This is where we read in from BOA the command line argument.
# If in your script, you use any other command line arguments,
# generally BOA's trial_dir should be the last command line arugment,
# so taking the last one should generally be safe.
args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]

# this this trial_dir folder there are 2 files supplied by BOA,
# a parameters.json that has just the parameters, and a trial.json
# that includes the parameters and a lot more in case you need it.
# Most people will only need the parameters.json
param_path <- file.path(trial_dir, "parameters.json")
data <- read_json(path=param_path)

# The parameter keys config from whatever you  named them in your
# config file, which you are free to change.
x0 <- data$x0
x1 <- data$x1
x2 <- data$x2
x3 <- data$x3
x4 <- data$x4
x5 <- data$x5

# We write out are data to another file for our run_model.R script
# in a real use case, this could be writing out the parameters
# to whatever config file your model needs whether it is
# json, a text file, yaml, toml, netcdf, or anything else.
# this just allows you to partition the conversion steps from
# BOA parameters.json to what your model will read
X <- c(x0, x1, x2, x3, x4, x5)
df <- data.frame(X)
write.csv(df, file.path(trial_dir, "data.csv"), row.names = FALSE)