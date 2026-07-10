import requests
import csv
import time
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import HTTPError, Timeout
import logging

# ========== CONFIGURATION ==========
NHTSA_API_BASE = "https://crashviewer.nhtsa.dot.gov/CrashAPI"
FROM_YEAR = 2020
TO_YEAR = 2023
FORMAT = "json"
HEADERS = {
    "X-Forwarded-For": "8.8.8.8",  # Simulated US IP
    "User-Agent": "Mozilla/5.0"
}
MIN_VEHICLES = 1
MAX_VEHICLES = 99
MAX_WORKERS = 100  # Increased for more concurrency

# List of all U.S. states and territories with NHTSA codes
STATES = [
    (1, "Alabama")
]

# Set up logging
logging.basicConfig(filename="crash_data.log", level=logging.INFO)

# Create a session for connection pooling
session = requests.Session()

# ========== FUNCTION TO FETCH CRASH LIST ==========
def fetch_crash_case_list(state, from_year, to_year):
    time.sleep(1)  # 1-second delay between each hit
    url = f"{NHTSA_API_BASE}/crashes/GetCaseList"
    params = {
        "states": state,
        "fromYear": from_year,
        "toYear": to_year,
        "minNumOfVehicles": MIN_VEHICLES,
        "maxNumOfVehicles": MAX_VEHICLES,
        "format": FORMAT
    }

    response = session.get(url, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    # CASE 1: Response contains a 'Results' list
    if isinstance(data, dict) and "Results" in data:
        crashes = data["Results"]
        if isinstance(crashes, list) and crashes and isinstance(crashes[0], list):
            # Flatten nested list
            flat_crashes = crashes[0]
            return flat_crashes
        elif isinstance(crashes, list) and all(isinstance(item, dict) for item in crashes):
            return crashes

    # CASE 2: Response is a nested list [[dict, dict, ...]]
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
        flat_data = data[0]
        return flat_data

    # CASE 3: Unexpected structure
    raise ValueError("Unexpected response format from API")

# ========== FUNCTION TO FETCH CRASH DETAILS ==========
def fetch_crash_details(case_year, state, state_case_id, retries=3, delay=300):  # 5-minute delay (300 seconds)
    time.sleep(1)  # 1-second delay between each hit
    url = f"{NHTSA_API_BASE}/crashes/GetCaseDetails"
    params = {
        "caseYear": case_year,
        "state": state,
        "stateCase": state_case_id,
        "format": FORMAT
    }

    for attempt in range(retries):
        try:
            response = session.get(url, params=params, headers=HEADERS, timeout=30)  # 30-second timeout
            response.raise_for_status()
            data = response.json()

            if not data or not isinstance(data, dict):
                raise ValueError(f"No valid crash details for ID {state_case_id}")
            return data
        except HTTPError as e:
            if e.response.status_code == 429:  # Rate limit exceeded
                if attempt < retries - 1:
                    time.sleep(delay)  # 5-minute delay on retry
                    continue
            raise
        except Timeout:
            logging.error(f"API stopped responding (timeout) for crash ID {state_case_id} in state {state}, case year {case_year}")
            raise
        except Exception as e:
            logging.error(f"Error fetching details for {state_case_id}: {e}")
            raise
    raise ValueError(f"Failed to fetch details for ID {state_case_id} after {retries} attempts")

# ========== FUNCTION TO PROCESS A SINGLE CRASH ==========
def process_crash(crash, state):
    if not isinstance(crash, dict):
        return None

    state_case_id = crash.get("St_Case") or crash.get("st_case")
    case_year = crash.get("case_year") or FROM_YEAR  # Fallback to FROM_YEAR

    if not state_case_id:
        return None

    try:
        details = fetch_crash_details(case_year, state, state_case_id)

        # Navigate to CrashResultSet
        crash_data = {}
        if "Results" in details and isinstance(details["Results"], list) and details["Results"]:
            results = details["Results"][0]
            if isinstance(results, list) and results and isinstance(results[0], dict) and "CrashResultSet" in results[0]:
                crash_data = results[0]["CrashResultSet"]

        # Construct CRASH_DATE from YEAR, MONTH, DAY, HOUR, MINUTE
        crash_date = (crash_data.get("YEAR", "") + "-" + 
                      str(crash_data.get("MONTH", "")).zfill(2) + "-" + 
                      str(crash_data.get("DAY", "")).zfill(2) + " " + 
                      str(crash_data.get("HOUR", "")).zfill(2) + ":" + 
                      str(crash_data.get("MINUTE", "")).zfill(2))

        # Create record with specified fields mapped to JSON response
        record = {
            # GetCaseList fields
            "Crash ID": state_case_id,
            "CrashDate": crash.get("CrashDate", ""),
            "CountyName": crash.get("CountyName", ""),
            "Fatals": crash.get("Fatals", ""),
            "Peds": crash.get("Peds", ""),
            "Persons": crash.get("Persons", ""),
            "State": crash.get("State", ""),
            "StateName": crash.get("StateName", ""),
            "TotalVehicles": crash.get("TotalVehicles", ""),
            # GetCaseDetails fields
            "Crash Date": crash_date,
            "Latitude": crash_data.get("LATITUDE", ""),
            "Longitude": crash_data.get("LONGITUD", ""),
            "Weather": crash_data.get("WEATHER", ""),
            "Weather Name": crash_data.get("WEATHERNAME", ""),
            "Road Function": crash_data.get("ROAD_FNC", ""),
            "Road Function Name": crash_data.get("ROAD_FNCNAME", ""),
            "Light Condition": crash_data.get("LGT_COND", ""),
            "Light Condition Name": crash_data.get("LGT_CONDNAME", ""),
            "Manner of Collision": crash_data.get("MAN_COLL", ""),
            "Manner of Collision Name": crash_data.get("MAN_COLLNAME", ""),
            "Speed Limit": crash_data.get("SP_JUR", ""),
            "Speed Limit Name": crash_data.get("SP_JURNAME", ""),
            "Harmful Event": crash_data.get("HARM_EV", ""),
            "Harmful Event Name": crash_data.get("HARM_EVNAME", ""),
            "Drunk Drivers": crash_data.get("DRUNK_DR", ""),
            "City": crash_data.get("CITY", ""),
            "City Name": crash_data.get("CITYNAME", ""),
            "Functional System": crash_data.get("FUNC_SYS", ""),
            "Functional System Name": crash_data.get("FUNC_SYSNAME", ""),
            "Work Zone": crash_data.get("WRK_ZONE", ""),
            "Work Zone Name": crash_data.get("WRK_ZONENAME", "")
        }
        return record
    except Exception as e:
        logging.error(f"Error processing crash {state_case_id}: {e}")
        return None

# ========== MAIN PIPELINE FUNCTION ==========
def run_pipeline():
    for state_id, state_name in STATES:
        crashes = []
        for year in range(FROM_YEAR, TO_YEAR + 1):
            try:
                year_crashes = fetch_crash_case_list(state_id, year, year)
                crashes.extend(year_crashes)
                logging.info(f"Fetched {len(year_crashes)} crashes for {state_name} in {year}")
            except Exception as e:
                logging.error(f"Error fetching crash list for {state_name} in {year}: {e}")
                continue

        output = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_crash = {executor.submit(process_crash, crash, state_id): crash for crash in crashes}
            for future in tqdm(as_completed(future_to_crash), total=len(crashes), desc=f"Processing crashes for {state_name}"):
                record = future.result()
                if record:
                    output.append(record)

        if output:
            with open(f"crash_data_{state_name}.csv", "w", newline='') as file:
                writer = csv.DictWriter(file, fieldnames=output[0].keys())
                writer.writeheader()
                writer.writerows(output)

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    try:
        run_pipeline()
    finally:
        session.close()