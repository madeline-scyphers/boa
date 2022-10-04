library(jsonlite)

args <- commandArgs(trailingOnly=TRUE)
data_path <- args[1]
data <- read_json(path=data_path)

trial_dir <- data$trial_dir

is_completed <- file.exists(file.path(trial_dir, "run_model_from_wrapper.json"))

if (is_completed) {
    trial_status <- "COMPLETED"
} else {
    trial_status <- "RUNNING"
}

out_data <- list(
    TrialStatus=unbox(trial_status)
)
json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "set_trial_status_from_wrapper.json"))