library(jsonlite)

branin <- function(x1, x2) {

    a <- 1
    b <- 5.1/(4*pi^2)
    c <- 5/pi
    r <- 6
    s <- 10
    t <- 1/(8*pi)

    term1 <- a * (x2 - b*x1^2 + c*x1 - r)^2
    term2 <- s*(1-t)*cos(x1)

    y <- term1 + term2 + s
    return(y)
}

args <- commandArgs(trailingOnly=TRUE)

data_path <- args[1]
data <- read_json(path=data_path)

trial_dir <- data$trial_dir

x1 <- data$parameters$x0
x2 <- data$parameters$x1
res <- branin(x1, x2)

out_data <- list(
    output=unbox(res)
)
json_data <- toJSON(out_data, pretty = TRUE)
print(json_data)
write(json_data, file.path(trial_dir, "run_model_from_wrapper.json"))