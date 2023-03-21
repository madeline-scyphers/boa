library(jsonlite)

BRANIN_TRUE_MIN <- 0.397887

args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]

# Read in our data
model_data <- read_json(path=file.path(trial_dir, "model_data.json"))
res <- model_data$output

# format and save our data to a format that BOA is expecting
out_data <- list(
    metric=list(
        a=res
    )
)

json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "output.json"))