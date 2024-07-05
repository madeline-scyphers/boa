# load in any libraries and modules we need
library(jsonlite)

# This is where we read in from BOA the command line argument.
# If in your script, you use any other command line arguments,
# generally BOA's trial_dir should be the last command line arugment,
# so taking the last one should generally be safe.
args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]

out_data <- list(
        trial_status=unbox("FAILED")
    )

json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "output.json"))
