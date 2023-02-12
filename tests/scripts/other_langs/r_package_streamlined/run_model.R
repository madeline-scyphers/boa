library(jsonlite)

hartman6 <- function(X) {
     out <- tryCatch(
     {
          alpha <- c(1.0, 1.2, 3.0, 3.2)
          A <- c(10, 3, 17, 3.5, 1.7, 8,
                 0.05, 10, 17, 0.1, 8, 14,
                 3, 3.5, 1.7, 10, 17, 8,
                 17, 8, 0.05, 10, 0.1, 14)
          A <- matrix(A, 4, 6, byrow=TRUE)
          P <- 10^(-4) * c(1312, 1696, 5569, 124, 8283, 5886,
                           2329, 4135, 8307, 3736, 1004, 9991,
                           2348, 1451, 3522, 2883, 3047, 6650,
                           4047, 8828, 8732, 5743, 1091, 381)
          P <- matrix(P, 4, 6, byrow=TRUE)

          Xmat <- matrix(rep(X,times=4), 4, 6, byrow=TRUE)
          inner_sum <- rowSums(A[,1:6]*(Xmat-P[,1:6])^2)
          outer_sum <- sum(alpha * exp(-inner_sum))
          y <- -outer_sum
          return(y)
     },
       error=function(cond) {
            return(NA)
        }
     )
    return(out)
}

args <- commandArgs(trailingOnly=TRUE)

trial_dir <- args[1]
param_path <- file.path(trial_dir, "parameters.json")
data <- read_json(path=param_path)

x0 <- data$x0
x1 <- data$x1
x2 <- data$x2
x3 <- data$x3
x4 <- data$x4
x5 <- data$x5
X <- c(x0, x1, x2, x3, x4, x5)
print(X)
res <- hartman6(X)

if (!is.na(res)) {

    # if it was a success, we don't even need to write out trial status,
    # it is assumed a success if we write out data and don't fail

    out_data <- list(
        mean=list(
            a=res
        ),
        trial_status=unbox("COMPLETED")
    )

    json_data <- toJSON(out_data, pretty = TRUE)
    write(json_data, file.path(trial_dir, "output.json"))
} else {
    trial_status <- "FAILED"
    out_data <- list(
        trial_status=unbox(trial_status)
    )
    json_data <- toJSON(out_data, pretty = TRUE)
    write(json_data, file.path(trial_dir, "output.json"))
}