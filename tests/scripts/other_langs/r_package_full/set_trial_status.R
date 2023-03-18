library(jsonlite)

args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]


# We read in the data we saved before.
# If it is just your own output data, you can probably put this step
# at the end of your Run Model Scipt. But if you don't know when
# your model finishes because it is running on an HPC,
# you could replace this with checks of the queue, or reading the log
# file for certain statuses, or other techniques.
data <- read_json(path=file.path(trial_dir, "model_data.json"))
is_passed <- (!is.na(data$output))

if (is_passed) {
    # If we passed, we write out the trial status as COMPLETE
    trial_status <- "COMPLETED"
    out_data <- list(
        trial_status=unbox(trial_status)
    )

} else {
    # If we failed, we write out the trial status as FAILED
    out_data <- list(
        trial_status=unbox("FAILED")
    )
}

# save to a trial_status.json file in the triad_dir
json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "trial_status.json"))