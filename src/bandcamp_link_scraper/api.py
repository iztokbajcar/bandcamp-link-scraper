from fastapi import FastAPI, HTTPException
from get_songs import get_songs, Song
import os
import requests
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


def download_songs(
    songs: list[Song],
    real_directory: str = "/tmp",
    playlist_song_directory: str = "/music",
) -> list[Song]:
    """Downloads all songs into the specified directory and returns a playlist containing the downloaded files, with links in the playlist
    having the prefix defined in playlist_song_directory instead of the real download directory."""

    for song in songs:
        escaped_artist = song.artist.replace("/", "_")
        escaped_title = song.title.replace("/", "_")
        filename = os.path.join(
            real_directory, f"{escaped_artist} - {escaped_title}.mp3"
        )

        # download song if it doesn't exist
        if not os.path.exists(filename):
            req = requests.get(song.url, allow_redirects=True)
            with open(filename, "wb") as f:
                f.write(req.content)
        else:
            print(f"Song {song.artist} - {song.title} already downloaded")
        # change song url to local path
        filename_in_playlist = os.path.join(
            playlist_song_directory, f"{escaped_artist} - {escaped_title}.mp3"
        )
        song.url = filename_in_playlist

    return songs


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
async def download(url: str, directory, playlist_song_directory):
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory not found")

    data = get_songs(url)
    local_songs = download_songs(data["songs"], directory, playlist_song_directory)
    playlist = parse_to_m3u8(local_songs)
    return {"art_url": data["art"], "m3u8": playlist}


@app.post("/bulk_download/")
async def bulk_download(urls: list[str], directory: str, playlist_song_directory: str):
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory not found")

    songs = []
    for url in urls:
        data = get_songs(url)
        local_songs = download_songs(data["songs"], directory, playlist_song_directory)
        songs.extend(local_songs)
    playlist = parse_to_m3u8(songs)
    return {"art_url": data["art"], "m3u8": playlist}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
