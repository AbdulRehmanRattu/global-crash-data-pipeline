# Increase download timeout
options(timeout = 600)

# Install and load required packages
if (!require(stats19)) {
  install.packages("stats19")
  library(stats19)
} else {
  library(stats19)
}

if (!require(curl)) {
  install.packages("curl")
  library(curl)
}

if (!require(progress)) {
  install.packages("progress")
  library(progress)
}

# Set the range of years from 2015 to the latest available
years <- 2015:2023  # Update to 2024 if available

# Initialize an empty list to store yearly data
accident_data_list <- list()

# Create a progress bar
pb <- progress_bar$new(
  format = "Downloading [:bar] :percent Year :current/:total",
  total = length(years),
  width = 60
)

# Loop through each year and download accident data
for (yr in years) {
  pb$tick()  # Update progress bar
  message(paste("Downloading data for year:", yr))
  tryCatch({
    acc <- get_stats19(year = yr, type = "accident", ask = FALSE)
    accident_data_list[[as.character(yr)]] <- acc
  }, error = function(e) {
    message(paste("Error downloading data for year:", yr, " - ", e$message))
  })
}

# Combine all years into a single data frame
all_accidents <- do.call(rbind, accident_data_list)

# Preview first few rows
print(head(all_accidents))

# Save combined data to a CSV file
write.csv(all_accidents, file = "uk_road_accidents_2015_to_latest.csv", row.names = FALSE)

message("✅ All data saved to 'uk_road_accidents_2015_to_latest.csv'")