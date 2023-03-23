library(jsonlite)
source("../r_utils/hartman6.R")

# This is where we read in from BOA the command line argument.
# If in your script, you use any other command line arguments,
# generally BOA's trial_dir should be the last command line arugment,
# so taking the last one should generally be safe.
args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]

param_path <- file.path(trial_dir, "parameters.json")
data <- read_json(path=param_path)

x0 <- data$x0
x1 <- data$x1
x2 <- data$x2
x3 <- data$x3
x4 <- data$x4
x5 <- data$x5
X <- c(x0, x1, x2, x3, x4, x5)

res <- hartman6(X)

if (!is.na(res)) {
    out_data <- list(
        TrialStatus=unbox("COMPLETED")
    )
    json_data <- toJSON(out_data, pretty = TRUE)
    write(json_data, file.path(trial_dir, "TrialStatus.json"))


    out_data <- list(
        metric=list(
            a=res
        )
    )

    json_data <- toJSON(out_data, pretty = TRUE)
    write(json_data, file.path(trial_dir, "output.json"))
} else {
    out_data <- list(
        TrialStatus=unbox("FAILED")
    )
    json_data <- toJSON(out_data, pretty = TRUE)
    write(json_data, file.path(trial_dir, "TrialStatus.json"))
}