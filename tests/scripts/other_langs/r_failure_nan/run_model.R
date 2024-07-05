library(jsonlite)
args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]
out_data <- list(
    metric=NaN
)
json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "output.json"))
