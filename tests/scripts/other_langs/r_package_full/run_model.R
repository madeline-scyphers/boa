library(jsonlite)
source("../r_utils/hartman6.R")

args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]

# Here we read the data we wrote out from our write_configs.R script
df <- read.csv(file = file.path(trial_dir, "data.csv"))
X <- df[[1]]

# This is where we actually run our "model".
# Here we are using a synthetic function called hartman6
# But you could substitute it for your own model in
# a number of ways.
res <- hartman6(X)

# Here we write out the data to wherever we want to store it,
# in this case we use the trial_dir
out_data <- list(
    output=unbox(res)
)
json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "model_data.json"))