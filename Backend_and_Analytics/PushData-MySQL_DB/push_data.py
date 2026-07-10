from fastapi import FastAPI, UploadFile, File, HTTPException
import pyodbc
import pandas as pd
import io
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(title="Database Management API")

# Function to get database connection
def get_db_connection(database=None):
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER=sql-server-fars.database.windows.net;"
            f"DATABASE={database or 'master'};"
            f"UID=sqladmin;"
            f"PWD=35#e9M5RgReL8NH;"
        )
        return pyodbc.connect(conn_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# Models
class TableInfo(BaseModel):
    table_name: str
    
class CSVUploadInfo(BaseModel):
    table_name: str
    database_name: str
    create_if_not_exists: bool = True

# Endpoints
@app.get("/databases")
def get_databases():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sys.databases")
        databases = [row[0] for row in cursor.fetchall()]
        return {"databases": databases}
    finally:
        conn.close()


@app.get("/tables/{database_name}")
def get_tables(database_name: str):
    conn = get_db_connection(database_name)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
        return {"database": database_name, "tables": tables}
    finally:
        conn.close()

@app.get("/columns/{database_name}/{table_name}")
def get_columns(database_name: str, table_name: str):
    conn = get_db_connection(database_name)
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
        """, table_name)
        columns = [{"name": row[0], "type": row[1], "nullable": row[2], "default": row[3]} for row in cursor.fetchall()]
        return {"database": database_name, "table": table_name, "columns": columns}
    finally:
        conn.close()

@app.post("/upload-csv")
async def upload_csv(database_name: str, table_name: str, create_if_not_exists: bool = True, 
                     file: UploadFile = File(...)):

    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Read CSV content
    contents = await file.read()
    try:
        # Add error handling for numeric data
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Clean the dataframe - replace problematic values
        for col in df.columns:
            # For columns that should be float, handle conversion issues
            if df[col].dtype == 'float64':
                # Convert to numeric, coerce errors to NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
            elif df[col].dtype == 'object':
                # For string columns that might contain numbers
                # Try to convert potential numeric columns
                try:
                    numeric_col = pd.to_numeric(df[col], errors='coerce')
                    # If more than 80% of values converted successfully, use this column as numeric
                    if numeric_col.notna().sum() > 0.8 * len(numeric_col):
                        df[col] = numeric_col
                except:
                    pass
                
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    conn = get_db_connection(database_name)
    try:
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = ? AND TABLE_CATALOG = ?
        """, (table_name, database_name))
        table_exists = cursor.fetchone()[0] > 0

        if not table_exists:
            if not create_if_not_exists:
                raise HTTPException(status_code=404, detail=f"Table {table_name} does not exist")

            # Create table based on CSV columns
            columns_def = []
            for col in df.columns:
                col_name = col.replace(" ", "_")
                if df[col].dtype == 'int64':
                    col_type = "INT"
                elif df[col].dtype == 'float64':
                    col_type = "FLOAT"
                elif df[col].dtype == 'bool':
                    col_type = "BIT"
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    col_type = "DATETIME"
                else:
                    max_length = df[col].astype(str).map(len).max()
                    max_length = max(max_length, 255)
                    col_type = f"VARCHAR({max_length})"

                columns_def.append(f"[{col_name}] {col_type}")

            create_sql = f"CREATE TABLE [{table_name}] ({', '.join(columns_def)})"
            cursor.execute(create_sql)
            conn.commit()

            # Handle insertion with proper value conversion
            # Convert DataFrame to a list of lists for insertion
            data_to_insert = []
            for _, row in df.iterrows():
                # Replace NaN with None for SQL compatibility
                row_values = [None if pd.isna(val) else val for val in row]
                data_to_insert.append(tuple(row_values))
            
            # Column names potentially have spaces replaced with underscores
            clean_column_names = [col.replace(" ", "_") for col in df.columns]
            placeholders = ', '.join(['?'] * len(clean_column_names))
            columns = ', '.join([f"[{col}]" for col in clean_column_names])
            
            insert_sql = f"INSERT INTO [{table_name}] ({columns}) VALUES ({placeholders})"
            
            # Execute in batches to avoid memory issues with large files
            batch_size = 1000
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i+batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            return {
                "message": f"Table {table_name} created and {len(df)} rows inserted",
                "rows_inserted": len(df)
            }

        else:
            # Table exists: fetch existing column names and types
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ? AND TABLE_CATALOG = ?
            """, (table_name, database_name))
            
            existing_columns = {}
            for row in cursor.fetchall():
                existing_columns[row[0]] = row[1]
            
            csv_columns = df.columns.tolist()
            matching_columns = [col for col in csv_columns if col in existing_columns]

            if not matching_columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"No matching columns found. CSV: {csv_columns}, Table: {list(existing_columns.keys())}"
                )

            # Select only matching columns from CSV
            df_subset = df[matching_columns]
            
            # Convert data types to match database schema
            for col in matching_columns:
                # Handle float columns specifically
                if existing_columns[col].upper() in ('FLOAT', 'REAL', 'DECIMAL', 'NUMERIC'):
                    df_subset[col] = pd.to_numeric(df_subset[col], errors='coerce')
                # Handle integer columns
                elif existing_columns[col].upper() in ('INT', 'BIGINT', 'SMALLINT', 'TINYINT'):
                    df_subset[col] = pd.to_numeric(df_subset[col], errors='coerce').astype('Int64')  # nullable integer
            
            # Handle insertion with proper value conversion
            data_to_insert = []
            for _, row in df_subset.iterrows():
                # Replace NaN with None for SQL compatibility
                row_values = [None if pd.isna(val) else val for val in row]
                data_to_insert.append(tuple(row_values))
            
            placeholders = ', '.join(['?'] * len(matching_columns))
            columns_str = ', '.join([f"[{col}]" for col in matching_columns])
            insert_sql = f"INSERT INTO [{table_name}] ({columns_str}) VALUES ({placeholders})"
            
            # Execute in batches
            batch_size = 1000
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i+batch_size]
                cursor.executemany(insert_sql, batch)
                conn.commit()

            return {
                "message": f"Data inserted into existing table {table_name}",
                "rows_inserted": len(df_subset),
                "columns_matched": matching_columns
            }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        conn.close()
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)