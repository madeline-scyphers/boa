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