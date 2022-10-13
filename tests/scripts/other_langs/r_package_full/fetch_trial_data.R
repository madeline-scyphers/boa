library(jsonlite)

BRANIN_TRUE_MIN <- 0.397887

args <- commandArgs(trailingOnly=TRUE)

data_path <- args[1]
data <- read_json(path=data_path)
trial_dir <- data$trial_dir

model_data <- read_json(path=file.path(trial_dir, "model_data.json"))
res <- model_data$output

out_data <- list(
    mean=list(
        a=res
    )
)

json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "output.json"))