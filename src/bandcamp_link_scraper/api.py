from fastapi import FastAPI
from get_songs import get_songs, Song
import uvicorn

app = FastAPI()

# parse functions
def parse_to_m3u8(songs: list[Song]):
    return "\n".join([str(song) for song in songs])

def parse_to_annotated_m3u8(songs: list[Song]):
    def annotate_song(song: Song):
        sanitized_artist = str(song.artist).replace('"', '\\"')
        sanitized_title = str(song.title).replace('"', '\\"')
        return f"annotate:artist=\"{sanitized_artist}\",title=\"{sanitized_title}\":{song.url}"

    annotated = list(map(annotate_song, songs))
    return "\n".join(annotated)

@app.get("/songs/")
async def songs(url: str):
    playlist = get_songs(url, parse_to_m3u8)
    return {"m3u8": playlist}

@app.get("/songs_annotated/")
async def songs_annotated(url: str):
    playlist = get_songs(url, parse_to_annotated_m3u8)
    return {"m3u8": playlist}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
