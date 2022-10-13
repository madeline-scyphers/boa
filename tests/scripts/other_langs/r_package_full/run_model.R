library(jsonlite)

# Maybe can use branin later?
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

hartman6 <- function(X) {
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
}

args <- commandArgs(trailingOnly=TRUE)

trial_dir <- args[1]

df <- read.csv(file = file.path(trial_dir, "data.csv"))
X <- df[[1]]
res <- hartman6(X)
# res <- branin(x1, x2)

out_data <- list(
    output=unbox(res)
)
json_data <- toJSON(out_data, pretty = TRUE)
print(json_data)
write(json_data, file.path(trial_dir, "model_data.json"))