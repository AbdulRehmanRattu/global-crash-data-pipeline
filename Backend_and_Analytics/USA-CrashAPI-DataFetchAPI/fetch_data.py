import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
from io import StringIO

app = FastAPI()

NHTSA_URL = "https://crashviewer.nhtsa.dot.gov/CrashAPI/FARSData/GetFARSData"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

@app.get("/fetch-nhtsa-data")
async def fetch_nhtsa_data(
    dataset: str = Query(...),
    FromYear: int = Query(...),
    ToYear: int = Query(...),
    format: str = Query("csv")
):
    try:
        proxy_url = "https://18.236.65.56:3129"
        transport = httpx.AsyncHTTPTransport(proxy=proxy_url, verify=False)

        async with httpx.AsyncClient(transport=transport, timeout=30.0, headers=HEADERS) as client:
            response = await client.get(
                NHTSA_URL,
                params={"dataset": dataset, "FromYear": FromYear, "ToYear": ToYear, "format": format}
            )

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Failed to fetch NHTSA data: {response.text[:300]}")

        if format == "csv":
            df = pd.read_csv(StringIO(response.text), low_memory=False)
            df_clean = df.replace([float("inf"), float("-inf")], None).fillna(None)
            return JSONResponse(content=df_clean.to_dict(orient="records"))

        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)