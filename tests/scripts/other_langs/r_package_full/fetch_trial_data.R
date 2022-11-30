library(jsonlite)

BRANIN_TRUE_MIN <- 0.397887

args <- commandArgs(trailingOnly=TRUE)

trial_dir <- args[1]

model_data <- read_json(path=file.path(trial_dir, "model_data.json"))
res <- model_data$output

out_data <- list(
    mean=list(
        a=res
    )
)

json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "output.json"))