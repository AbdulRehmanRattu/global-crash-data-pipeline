# Enhanced FastAPI code implementing advanced risk scoring based on fatality severity and combinations
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import folium
from folium.plugins import HeatMap
import numpy as np
import uuid
import os
from typing import Dict, Any

app = FastAPI(title="Enhanced Accident Risk Score API")
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class AccidentQuery(BaseModel):
    latitude: float
    longitude: float
    hour: int
    day_of_week: int
    weather: str
    lighting: str
    return_map: bool = True
    lat_margin: float = 0.5
    lon_margin: float = 0.5

    class Config:
        schema_extra = {
            "example": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "hour": 15,
                "day_of_week": 5,
                "weather": "Rain",
                "lighting": "Dark - Not Lighted",
                "return_map": True
            }
        }

# Global variables
df_all = None
TOP_GRID_COMBOS = None
EXTREME_WEATHER = {"Blowing Sand, Soil, Dirt", "Sleet or Hail", "Severe Crosswinds"}

@app.on_event("startup")
async def load_data():
    global df_all, TOP_GRID_COMBOS
    df = pd.read_csv("../../Data/USA_data/Accidents_2015_2023.csv", usecols=[
        "latitude", "longitud", "weathername", "lgt_condname", "hour", "day_weekname", "fatals", "statename", "cityname", "countyname"
    ], low_memory=False)
    df.dropna(subset=["latitude", "longitud"], inplace=True)
    df["latitude"] = df["latitude"].astype(float)
    df["longitud"] = df["longitud"].astype(float)
    df_all = df

    # Load top grid combinations for extreme volume (assume precomputed)
    try:
        TOP_GRID_COMBOS = pd.read_csv("../rule_based_accident_prediction/accident_fastapi/data/top_grids.csv")
    except:
        TOP_GRID_COMBOS = pd.DataFrame(columns=["lat_grid", "lon_grid"])

# Define core logic for risk score

def calculate_risk_score(hour, day, lighting, weather, is_hotspot, is_extreme_grid, is_extreme_combo):
    score = 0
    if hour in range(13, 18):
        score += 1
    if day in {5, 6, 7}:
        score += 1
    if lighting in {"Dusk", "Dawn", "Dark - Not Lighted", "Dark - Unknown Lighting"}:
        score += 3
    elif lighting in {"Dark - Lighted"}:
        score += 2
    if weather in EXTREME_WEATHER:
        score += 4
    elif weather in {"Rain", "Fog, Smog, Smoke", "Snow", "Freezing Rain or Drizzle"}:
        score += 3
    if is_hotspot:
        score += 2
    if is_extreme_grid:
        score += 1
    if is_extreme_combo:
        score += 1
    return score

def analyze_risk(query: Dict[str, Any]) -> Dict[str, Any]:
    lat, lon = query["latitude"], query["longitude"]
    lat_margin, lon_margin = query["lat_margin"], query["lon_margin"]
    lat_min, lat_max = lat - lat_margin, lat + lat_margin
    lon_min, lon_max = lon - lon_margin, lon + lon_margin

    df_local = df_all[
        (df_all["latitude"] >= lat_min) & (df_all["latitude"] <= lat_max) &
        (df_all["longitud"] >= lon_min) & (df_all["longitud"] <= lon_max)
    ].copy()

    if df_local.empty:
        return {"risk_score": 0, "is_high_risk": False, "map": None}

    # Grid check
    lat_step = 0.0025
    lon_step = 0.0025
    lat_edges = np.arange(lat_min, lat_max + lat_step, lat_step)
    lon_edges = np.arange(lon_min, lon_max + lon_step, lon_step)

    df_local["block_lat"] = np.searchsorted(lat_edges, df_local["latitude"]) - 1
    df_local["block_lon"] = np.searchsorted(lon_edges, df_local["longitud"]) - 1

    block_counts = df_local.groupby(["block_lat", "block_lon"]).size().reset_index(name="count")
    threshold = block_counts["count"].quantile(0.75)

    user_block_lat = np.searchsorted(lat_edges, lat) - 1
    user_block_lon = np.searchsorted(lon_edges, lon) - 1

    user_block = block_counts[
        (block_counts["block_lat"] == user_block_lat) & (block_counts["block_lon"] == user_block_lon)
    ]
    is_hotspot = bool(not user_block.empty and user_block.iloc[0]["count"] >= threshold)

    # Check if in extreme grid
    lat_grid = (lat // 5) * 5
    lon_grid = (lon // 5) * 5
    is_extreme_grid = bool(((TOP_GRID_COMBOS.lat_grid == lat_grid) & (TOP_GRID_COMBOS.lon_grid == lon_grid)).any())

    # Check if combination is high fatality risk (simplified: use known worst-case example logic)
    is_extreme_combo = bool(query["weather"] == "Fog, Smog, Smoke" and query["lighting"] == "Dark - Not Lighted")


    score = calculate_risk_score(
        query["hour"], query["day_of_week"], query["lighting"], query["weather"],
        is_hotspot, is_extreme_grid, is_extreme_combo
    )
    is_high_risk = score >= 6

    result = {
        "risk_score": score,
        "is_high_risk": is_high_risk,
        "is_hotspot": is_hotspot,
        "is_extreme_grid": is_extreme_grid,
        "is_extreme_combo": is_extreme_combo
    }

    if query.get("return_map"):
        fol_map = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker(
            [lat, lon],
            popup=f"Risk Score: {score}",
            icon=folium.Icon(color='red' if is_high_risk else 'green')
        ).add_to(fol_map)
        result["map"] = fol_map

    return result

@app.post("/risk-score/")
async def get_risk_score(query: AccidentQuery):
    try:
        result = analyze_risk(query.dict())
        if "map" in result and result["map"]:
            map_id = uuid.uuid4().hex
            filepath = f"static/risk_map_{map_id}.html"
            result["map"].save(filepath)
            result["map_url"] = f"/static/risk_map_{map_id}.html"
        result.pop("map", None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)