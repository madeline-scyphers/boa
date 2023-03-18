# load in any libraries and modules we need
library(jsonlite)
source("../r_utils/hartman6.R")

# This is where we read in from BOA the command line argument.
# If in your script, you use any other command line arguments,
# generally BOA's trial_dir should be the last command line arugment,
# so taking the last one should generally be safe.
args <- commandArgs(trailingOnly=TRUE)
trial_dir <- args[length(args)]

# this this trial_dir folder there are 2 files supplied by BOA,
# a parameters.json that has just the parameters, and a trial.json
# that includes the parameters and a lot more in case you need it.
# Most people will only need the parameters.json
param_path <- file.path(trial_dir, "parameters.json")
data <- read_json(path=param_path)

# The parameter keys config from whatever you  named them in your
# config file, which you are free to change.
x0 <- data$x0
x1 <- data$x1
x2 <- data$x2
x3 <- data$x3
x4 <- data$x4
x5 <- data$x5
X <- c(x0, x1, x2, x3, x4, x5)

# This is where we actually run our "model".
# Here we are using a synthetic function called hartman6
# But you could substitute it for your own model in
# a number of ways.
res <- hartman6(X)

# In this case, we directly ran the model, so we are getting back a number
# or nan, so we know if it succeeded or failed. If you are submitting a job
# to an HPC (a super computer) queue, this might work, or you might have to
# rely on another method. Other options could be relying on log file output
# or information from querying the queue itself,
# though those may be better as stand alone `Set Trial Status Scripts`
if (!is.na(res)) {

    # if it was a success, we don't even need to write out trial status,
    # it is assumed a success if we write out data and don't fail
    out_data <- list(
        mean=list(
            a=res
        )
        # trial_status=unbox("COMPLETED")  #  this is optional if it succeeds
    )

} else {

    # If we fail, then we do need to include a trial status, and mark it as failed.
    out_data <- list(
        trial_status=unbox("FAILED")
    )
}

json_data <- toJSON(out_data, pretty = TRUE)
write(json_data, file.path(trial_dir, "output.json"))