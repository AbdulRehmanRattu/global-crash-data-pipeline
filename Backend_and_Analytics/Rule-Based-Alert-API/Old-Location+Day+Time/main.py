
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import folium
from folium.plugins import HeatMap
import numpy as np
import uuid
import os
from typing import Dict, Any

app = FastAPI(
    title="Accident Hotspot Analyzer (Local User Bounding Box)",
    description=(
        "API that computes a small bounding box around the user's location, "
        "assigns accidents to local grid blocks, and identifies hotspots."
    )
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


class AccidentQuery(BaseModel):
    latitude: float
    longitude: float
    hour: int
    day_of_week: int   
    return_map: bool = True      # Skip map creation if False
    lat_margin: float = 0.5      # +/- margin in degrees around user lat
    lon_margin: float = 0.5      # +/- margin in degrees around user lon

    class Config:
        schema_extra = {
            "example": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "hour": 13,
                "day_of_week": 2,
                "return_map": True,
                "lat_margin": 0.5,
                "lon_margin": 0.5
            }
        }


# GLOBAL DATA (entire dataset) loaded once
df_all = None

@app.on_event("startup")
async def load_accident_data():
    """
    Load your entire dataset once. But we won't precompute blocks. 
    We'll just keep df_all in memory for local bounding box queries.
    """
    global df_all
    try:
       
        df = pd.read_csv("data/df_combined.CSV", low_memory=False)

        required_cols = ["latitude", "longitud", "hour", "day_week"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        df.dropna(subset=required_cols, inplace=True)
        df["latitude"] = df["latitude"].astype(float)
        df["longitud"] = df["longitud"].astype(float)
        df["hour"] = df["hour"].astype(int)
        df["day_week"] = df["day_week"].astype(int)

        #  filter to continental US:
        df = df[
            (df["latitude"] >= 24.52) & (df["latitude"] <= 49.38) &
            (df["longitud"] >= -124.77) & (df["longitud"] <= -66.95)
        ].copy()

        df_all = df
        print(f"Loaded {len(df_all)} accident records into memory.")
    except Exception as e:
        raise RuntimeError(f"Data loading failed: {str(e)}")


def generate_hotspot_map_local(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    1) Create a bounding box around the user location: ± lat_margin, ± lon_margin
    2) Filter accidents by day/time, then by bounding box
    3) Create a local grid for just that bounding box
    4) Identify hotspots >= 75th percentile
    5) If return_map=False, skip Folium map building
    6) Otherwise, build map with polygons, heatmap
    """
    user_lat = query["latitude"]
    user_lon = query["longitude"]
    user_hour = query["hour"]
    user_day = query["day_of_week"]
    return_map = query.get("return_map", True)
    lat_margin = query.get("lat_margin", 0.5)
    lon_margin = query.get("lon_margin", 0.5)

    # 1) Filter by day_of_week and a 3-hour range around user_hour
    valid_days = [1, 2, 3, 4, 5] if user_day <= 5 else [6, 7]

 
    hour_min = max(0, user_hour - 3)  
    hour_max = min(23, user_hour + 3)   

    
    time_filter = (df_all["hour"] >= hour_min) & (df_all["hour"] <= hour_max)

    df_filtered = df_all[
        (df_all["day_week"].isin(valid_days)) & 
        time_filter
    ].copy()

    if df_filtered.empty:
        if not return_map:
            return {"map": None, "hotspot_nearby": False}
        fol_map = folium.Map(location=[user_lat, user_lon], zoom_start=12)
        folium.Marker([user_lat, user_lon],
                      popup="Your Location",
                      icon=folium.Icon(color='red')).add_to(fol_map)
        return {"map": fol_map, "hotspot_nearby": False}

 
    lat_min = user_lat - lat_margin
    lat_max = user_lat + lat_margin
    lon_min = user_lon - lon_margin
    lon_max = user_lon + lon_margin

    df_local = df_filtered[
        (df_filtered["latitude"] >= lat_min) & (df_filtered["latitude"] <= lat_max) &
        (df_filtered["longitud"] >= lon_min) & (df_filtered["longitud"] <= lon_max)
    ].copy()

    if df_local.empty:
        if not return_map:
            return {"map": None, "hotspot_nearby": False}
        fol_map = folium.Map(location=[user_lat, user_lon], zoom_start=12)
        folium.Marker([user_lat, user_lon],
                      popup="Your Location",
                      icon=folium.Icon(color='red')).add_to(fol_map)
        return {"map": fol_map, "hotspot_nearby": False}

 
    lat_step = 0.0025
    lon_step = 0.0025
    local_lat_edges = np.arange(lat_min, lat_max + lat_step, lat_step)
    local_lon_edges = np.arange(lon_min, lon_max + lon_step, lon_step)

    if len(local_lat_edges) < 2 or len(local_lon_edges) < 2:
       
        if not return_map:
            return {"map": None, "hotspot_nearby": False}
        fol_map = folium.Map(location=[user_lat, user_lon], zoom_start=12)
        folium.Marker([user_lat, user_lon],
                      popup="Your Location",
                      icon=folium.Icon(color='red')).add_to(fol_map)
        return {"map": fol_map, "hotspot_nearby": False}

    
    df_local["block_lat"] = np.searchsorted(local_lat_edges, df_local["latitude"]) - 1
    df_local["block_lon"] = np.searchsorted(local_lon_edges, df_local["longitud"]) - 1

   
    valid_idx = (
        (df_local["block_lat"] >= 0) & (df_local["block_lat"] < len(local_lat_edges)-1) &
        (df_local["block_lon"] >= 0) & (df_local["block_lon"] < len(local_lon_edges)-1)
    )
    df_local = df_local[valid_idx].copy()
    if df_local.empty:
        if not return_map:
            return {"map": None, "hotspot_nearby": False}
        fol_map = folium.Map(location=[user_lat, user_lon], zoom_start=12)
        folium.Marker([user_lat, user_lon],
                      popup="Your Location",
                      icon=folium.Icon(color='red')).add_to(fol_map)
        return {"map": fol_map, "hotspot_nearby": False}

 
    block_counts = df_local.groupby(["block_lat", "block_lon"]).size().reset_index(name="accident_count")
    if block_counts.empty:
        if not return_map:
            return {"map": None, "hotspot_nearby": False}
        fol_map = folium.Map(location=[user_lat, user_lon], zoom_start=12)
        folium.Marker([user_lat, user_lon],
                      popup="Your Location",
                      icon=folium.Icon(color='red')).add_to(fol_map)
        return {"map": fol_map, "hotspot_nearby": False}

 
    threshold_75 = block_counts["accident_count"].quantile(0.90)
    hotspots = block_counts[block_counts["accident_count"] >= threshold_75]

    
    hotspot_nearby = False
    for _, row in hotspots.iterrows():
        i = row["block_lat"]
        j = row["block_lon"]
        lat1 = local_lat_edges[i]
        lat2 = local_lat_edges[i + 1]
        lon1 = local_lon_edges[j]
        lon2 = local_lon_edges[j + 1]
        if (lat1 <= user_lat <= lat2) and (lon1 <= user_lon <= lon2):
            hotspot_nearby = True
            break

    
    if not return_map:
        return {"map": None, "hotspot_nearby": hotspot_nearby}

   
    fol_map = folium.Map(location=[user_lat, user_lon], zoom_start=12)

    
    hotspot_blocks = set(zip(hotspots["block_lat"], hotspots["block_lon"]))
    df_hotspot_points = df_local[
        df_local.apply(lambda r: (r["block_lat"], r["block_lon"]) in hotspot_blocks, axis=1)
    ]

    HeatMap(
        df_hotspot_points[["latitude", "longitud"]].values.tolist()
    ).add_to(fol_map)

    
    for _, row in hotspots.iterrows():
        i = row["block_lat"]
        j = row["block_lon"]
        lat1 = local_lat_edges[i]
        lat2 = local_lat_edges[i + 1]
        lon1 = local_lon_edges[j]
        lon2 = local_lon_edges[j + 1]

        polygon_coords = [
            [lat1, lon1],
            [lat1, lon2],
            [lat2, lon2],
            [lat2, lon1]
        ]
        folium.Polygon(
            locations=polygon_coords,
            popup=f"Accidents: {row['accident_count']}",
            tooltip=f"Accidents: {row['accident_count']}",
            color=None,
            fill=True,
            fill_color='red',
            fill_opacity=0.3
        ).add_to(fol_map)

 
    folium.Marker(
        location=[user_lat, user_lon],
        popup="Your Location",
        icon=folium.Icon(color='red')
    ).add_to(fol_map)

    return {"map": fol_map, "hotspot_nearby": hotspot_nearby}


@app.post("/analyze-accidents-local/", response_model=Dict[str, Any])
async def analyze_accidents_local(query: AccidentQuery):
    """
    Endpoint that uses a local bounding box around the user's location.
    Body example:
    {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "hour": 13,
      "day_of_week": 2,
      "return_map": true,
      "lat_margin": 0.5,
      "lon_margin": 0.5
    }
    """
    try:
        result = generate_hotspot_map_local(query.dict())
        
        # If no map is generated
        if result["map"] is None:
            return {
                "map_id": None,
                "map_url": None,
                "hotspot_nearby": result["hotspot_nearby"],
                "user_location": query.dict()
            }

        
        map_id = uuid.uuid4().hex
        filename = f"accident_map_{map_id}.html"
        filepath = os.path.join("static", filename)
        
        result["map"].save(filepath)
        
        return {
            "map_id": map_id,
            "map_url": f"/static/{filename}",
            "hotspot_nearby": result["hotspot_nearby"],
            "user_location": query.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)

