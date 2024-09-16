from html.parser import HTMLParser
import json
import sys
from urllib.request import Request, urlopen


class AlbumDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = {}

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            for attr, value in attrs:
                if attr == "data-tralbum":
                    self.data = json.loads(value)
                    break


class Song:
    def __init__(self, artist, title, url):
        self.artist = artist
        self.title = title
        self.url = url

    def __str__(self):
        return f"{self.url}  # {self.artist} - {self.title}"


def get_album_songs(album_url: str):
    # get the album page
    req = Request(album_url)
    response = urlopen(req).read().decode("utf-8")

    parser = AlbumDataParser()
    parser.feed(response)

    album_artist = parser.data["current"]["artist"]

    songs = []

    for d in parser.data["trackinfo"]:
        track_artist = d["artist"]
        if track_artist is None:
            track_artist = album_artist

        track_title = d["title"]
        track_url = d["file"]["mp3-128"]

        songs.append(Song(track_artist, track_title, track_url))

    album_playlist = "\n".join([str(song) for song in songs])
    return album_playlist


if __name__ == "__main__":
    if len(sys.argv) < 2:
        url = input("Enter album url: ")
    else:
        url = sys.argv[1]

    print(get_album_songs(url))
