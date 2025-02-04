from html.parser import HTMLParser
import json
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, ID3NoHeaderError
from mutagen.mp3 import MP3
import os
import requests
import sys
from urllib.request import Request, urlopen


class AlbumDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.passed_h3 = False
        self.passed_album_by = False
        self.reading_title = False
        self.reading_artist = False
        self.reading_album_art_div = False
        self.title = None
        self.artist = None
        self.album_art_url = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            for attr, value in attrs:
                if attr == "data-tralbum":
                    self.data = json.loads(value)
                    break

        if tag == "h2" and self.title is None:
            for attr, value in attrs:
                if attr == "class" and value == "trackTitle":
                    self.reading_title = True

        if tag == "h3" and self.artist is None:
            self.passed_h3 = True

        if tag == "a":
            if self.artist is None and self.passed_h3:
                if self.passed_album_by:
                    self.reading_artist = True

        if tag == "div" and self.album_art_url is None:
            for attr, value in attrs:
                if attr == "id" and value == "tralbumArt":
                    self.reading_album_art_div = True

        if tag == "a" and self.reading_album_art_div and self.album_art_url is None:
            for attr, value in attrs:
                if attr == "href":
                    self.album_art_url = value
                    self.reading_album_art_div = False
                    break

    def handle_data(self, data):
        if self.reading_title:
            self.title = data.strip()
            print(f"'{self.title}'")
            self.reading_title = False

        if self.passed_h3 and self.artist is None and not self.passed_album_by:
            if "by" in data:
                self.passed_album_by = True

        if self.reading_artist:
            self.artist = data.strip()
            print(f"'{self.artist}'")
            self.reading_artist = False


class Song:
    def __init__(
        self,
        artist: str,
        title: str,
        album: str,
        album_art_url: str,
        url: str,
        duration: float,
    ):
        self.artist = artist
        self.title = title
        self.album = album
        self.album_art_url = album_art_url
        self.url = url
        self.duration = duration
        print(f"song: {self.artist}, {self.title} | {self.album}")

    def __str__(self):
        return f"# {self.artist} - {self.title}\n{self.url}"


def fetch_page(album_url: str):
    # get the album page
    try:
        req = Request(album_url)
        response = urlopen(req).read().decode("utf-8")
        return response
    except Exception as e:
        # fetching failed, return an empty string
        # TODO log the error somewhere
        return ""


def get_songs(album_url: str):
    response = fetch_page(album_url)

    # if the fetching failed, return an empty string
    if len(response) == 0:
        return ""

    parser = AlbumDataParser()
    parser.feed(response)

    album_artist = parser.data["current"]["artist"]

    songs = []

    # deduce artist from the page title to later use it instead
    # of the artist present in tralbum if that turns out to be unavailable
    # this is useful for albums that are published by records, where
    # the song artist metadata doesn't actually represent the real artist
    page_artist = None
    album = None
    if " - " in parser.title:
        page_artist, album = parser.title.split(" - ")[:2]
    else:
        page_artist = parser.artist
        album = parser.title

    for d in parser.data["trackinfo"]:
        track_artist = d["artist"]
        if track_artist is None:
            if album_artist is not None:
                track_artist = album_artist
            else:
                track_artist = page_artist

        track_title = d["title"]
        track_duration = d["duration"]

        # handle the case where the song is not playable
        # (skip it if it has no file link)
        if d["file"] is None:
            print(
                f"WARNING: song '{track_title}' is not available for playing. Skipping it!"
            )
            continue

        track_url = d["file"]["mp3-128"]
        album_art_url = parser.album_art_url

        songs.append(
            Song(
                track_artist,
                track_title,
                album,
                album_art_url,
                track_url,
                track_duration,
            )
        )

    # album_playlist = parse_fun(songs)
    return {"art": album_art_url, "songs": songs}


def download_songs(
    songs: list[Song],
    real_directory: str = "/tmp",
    playlist_song_directory: str = "/music",
    force: bool = False,
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
        if not os.path.exists(filename) or force:
            req = requests.get(song.url, allow_redirects=True)
            with open(filename, "wb") as f:
                f.write(req.content)

                # set song metadata
                mp3 = None
                try:
                    mp3 = EasyID3(filename)
                except ID3NoHeaderError:
                    mp3 = mutagen.File(filename, easy=True)
                    mp3.add_tags()

                mp3["artist"] = song.artist
                mp3["album"] = song.album
                mp3["title"] = song.title
                mp3.save(filename, v2_version=3)

                # add album art
                if song.album_art_url is not None:
                    art_filename = os.path.join(
                        "/tmp", song.album_art_url.split("/")[-1]
                    )

                    art_contents = None

                    req = requests.get(song.album_art_url, allow_redirects=True)
                    if not os.path.exists(art_filename):
                        with open(art_filename, "wb") as f:
                            f.write(req.content)
                        art_contents = req.content
                    else:
                        with open(art_filename, "rb") as f:
                            art_contents = f.read()

                    mp3 = MP3(filename, ID3=ID3)
                    mp3.tags.add(
                        APIC(
                            encoding=3,
                            mime="image/jpeg",
                            type=3,
                            desc="Cover",
                            data=art_contents,
                        )
                    )
                    mp3.save(filename, v2_version=3)

            print(f"Downloaded song '{song.artist} - {song.title}'")
        else:
            print(f"Song '{song.artist} - {song.title}' already downloaded")
        # change song url to local path
        filename_in_playlist = os.path.join(
            playlist_song_directory, f"{escaped_artist} - {escaped_title}.mp3"
        )
        song.url = filename_in_playlist

    return songs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        url = input("Enter album url: ")
    else:
        url = sys.argv[1]

    print(get_songs(url))
