library(jsonlite)

args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[1]

is_completed <- file.exists(file.path(trial_dir, "model_data.json"))

if (is_completed) {
    trial_status <- "COMPLETED"
    out_data <- list(
        trial_status=unbox(trial_status)
    )
    json_data <- toJSON(out_data, pretty = TRUE)
    write(json_data, file.path(trial_dir, "trial_status.json"))
}