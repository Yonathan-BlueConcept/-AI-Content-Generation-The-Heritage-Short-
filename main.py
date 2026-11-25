import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "ok", "message": "FastAPI is running"}


@app.get("/test-api")
async def test_external_api():
    url = "https://httpbin.org/get"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"External API error: {exc}")