from fastapi import FastAPI
from get_songs import get_songs
import uvicorn

app = FastAPI()

@app.get("/songs/")
async def root(url: str):
    playlist = get_songs(url)
    return {"m3u8": playlist}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
