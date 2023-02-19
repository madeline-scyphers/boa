library(jsonlite)
source("../r_utils/hartman6.R")

# This is where we read in from BOA the command line argument.
# If in your script, you use any other command line arguments,
# generally BOA's trial_dir should be the last command line arugment,
# so taking the last one should generally be safe.
args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]

df <- read.csv(file = file.path(trial_dir, "data.csv"))
X <- df[[1]]
res <- hartman6(X)

out_data <- list(
    output=unbox(res)
)
json_data <- toJSON(out_data, pretty = TRUE)
print(json_data)
write(json_data, file.path(trial_dir, "model_data.json"))