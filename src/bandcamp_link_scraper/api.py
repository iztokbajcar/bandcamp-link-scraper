from fastapi import FastAPI, HTTPException
from get_songs import get_songs, download_songs, Song
import os
import uvicorn

app = FastAPI()


# parse functions
def parse_to_m3u8(songs: list[Song]):
    return "\n".join([str(song) for song in songs])


def parse_to_annotated_m3u8(songs: list[Song]):
    def annotate_song(song: Song):
        sanitized_artist = str(song.artist).replace('"', '\\"')
        sanitized_title = str(song.title).replace('"', '\\"')
        sanitized_album = str(song.album).replace('"', '\\"')
        duration = song.duration
        return f'annotate:artist="{sanitized_artist}",title="{sanitized_title}",album="{sanitized_album}",duration="{duration}":{song.url}'

    annotated = list(map(annotate_song, songs))
    return "\n".join(annotated)


@app.get("/songs/")
async def songs(url: str):
    data = get_songs(url)
    playlist = parse_to_m3u8(data["songs"])
    return {"art_url": data["art"], "m3u8": playlist}


@app.get("/songs_annotated/")
async def songs_annotated(url: str):
    data = get_songs(url)
    playlist = parse_to_annotated_m3u8(data["songs"])
    return {"art_url": data["art"], "m3u8": playlist}


@app.get("/download/")
async def download(
    url: str, directory: str, playlist_song_directory: str, force: str | None = None
):
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory not found")

    data = get_songs(url)
    local_songs = download_songs(
        data["songs"], directory, playlist_song_directory, force is not None
    )
    playlist = parse_to_m3u8(local_songs)
    return {"art_url": data["art"], "m3u8": playlist}


@app.post("/bulk_download/")
async def bulk_download(
    urls: list[str],
    directory: str,
    playlist_song_directory: str,
    force: str | None = None,
):
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory not found")

    songs = []
    for url in urls:
        data = get_songs(url)
        local_songs = download_songs(
            data["songs"], directory, playlist_song_directory, force is not None
        )
        songs.extend(local_songs)
    playlist = parse_to_m3u8(songs)
    return {"art_url": data["art"], "m3u8": playlist}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
