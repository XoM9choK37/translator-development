
# Пример программы на R
calculate_stats <- function(data) {
    mean_val <- mean(data, na.rm = TRUE)
    sd_val <- sd(data, na.rm = TRUE)
    
    if (mean_val > 0) {
        result <- list(
            mean = mean_val,
            sd = sd_val,
            n = length(data)
        )
        return(result)
    } else {
        return(NULL)
    }
}

# Тестовые данные
x <- c(1, 2, 3, 4, 5)
y <- x * 2 + rnorm(5, mean = 0, sd = 1)
t <- 12.

# Анализ
stats <- calculate_stats(x)
print(stats)

# Числа с плавающей точкой
z <- 3.14159
w <- 2.5e-3
