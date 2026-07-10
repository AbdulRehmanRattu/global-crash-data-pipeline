import os
import pandas as pd

def merge_csv_files(data_directory, output_path):
    # List to store dataframes
    dataframes = []

    # Check if the directory exists
    if not os.path.isdir(data_directory):
        print(f"Directory does not exist: {data_directory}")
        return

    # Loop through all files in the directory
    for file_name in os.listdir(data_directory):
        if file_name.lower().endswith('.csv'):
            file_path = os.path.join(data_directory, file_name)
            try:
                df = pd.read_csv(file_path)
                dataframes.append(df)
                print(f"Loaded: {file_name} with {len(df)} rows")
            except Exception as e:
                print(f"Failed to read {file_name}: {e}")

    if not dataframes:
        print("No CSV files found or loaded. Nothing to merge.")
        return

    # Vertically merge all dataframes
    merged_data = pd.concat(dataframes, ignore_index=True)

    merged_data.to_csv(output_path, index=False)

    print(f"All CSV files have been merged and saved as '{output_path}'.")

if __name__ == "__main__":
    input_dir_path = "../Data/UK_data"
    output_file_path = "../Data/UK_data/UK_Accidents_2019_2023.csv"
    merge_csv_files(input_dir_path, output_file_path)