from html.parser import HTMLParser
import json
import sys
from urllib.request import Request, urlopen


class AlbumDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.passed_h3 = False
        self.reading_title = False
        self.reading_artist = False
        self.title = None
        self.artist = None

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

        if tag == "a" and self.artist is None and self.passed_h3:
            self.reading_artist = True

    def handle_data(self, data):
        if self.reading_title:
            self.title = data.strip()
            print(f"'{self.title}'")
            self.reading_title = False

        if self.reading_artist:
            self.artist = data.strip()
            print(f"'{self.artist}'")
            self.reading_artist = False

class Song:
    def __init__(self, artist: str, title: str, url: str):
        self.artist = artist
        self.title = title
        self.url = url
        print(f"song: {self.artist}, {self.title}")

    def __str__(self):
        return f"# {self.artist} - {self.title}\n{self.url}"


def fetch_page(album_url: str):
    # get the album page
    req = Request(album_url)
    response = urlopen(req).read().decode("utf-8")  
    return response


def get_songs(album_url: str, parse_fun: object):
    response = fetch_page(album_url)
    parser = AlbumDataParser()
    parser.feed(response)

    album_artist = parser.data["current"]["artist"]

    songs = []

    # deduce artist from the page title to later use it instead
    # of the artist present in tralbum if that turns out to be unavailable
    # this is useful for albums that are published by records, where
    # the song artist metadata doesn't actually represent the real artist
    page_artist = None
    if " - " in parser.title:
        page_artist = parser.title.split(" - ")[0]
    else:
        page_artist = parser.artist

    for d in parser.data["trackinfo"]:
        track_artist = d["artist"]
        if track_artist is None:
            if album_artist is not None:
                track_artist = album_artist
            else:
                track_artist = page_artist

        track_title = d["title"]
        track_url = d["file"]["mp3-128"]

        songs.append(Song(track_artist, track_title, track_url))

    album_playlist = parse_fun(songs)
    return f"{album_playlist}\n"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        url = input("Enter album url: ")
    else:
        url = sys.argv[1]

    print(get_songs(url))
