library(jsonlite)

args <- commandArgs(trailingOnly=TRUE)
data_path <- args[1]
data <- read_json(path=data_path)

trial_dir <- data$trial_dir

is_completed <- file.exists(file.path(trial_dir, "model_data.json"))

if (is_completed) {
    trial_status <- "COMPLETED"
    out_data <- list(
        trial_status=unbox(trial_status)
    )
    json_data <- toJSON(out_data, pretty = TRUE)
    write(json_data, file.path(trial_dir, "trial_status.json"))
}