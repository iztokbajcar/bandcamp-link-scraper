from html.parser import HTMLParser
import json
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

        if tag == "a" and self.artist is None and self.passed_h3:
            if self.passed_album_by:
                self.reading_artist = True

        if tag == "div" and self.album_art_url is None:
            for attr, value in attrs:
                if attr == "id" and value == "tralbumArt":
                    self.reading_album_art = True

        if tag == "img" and self.reading_album_art_div and self.album_art_url is None:
            for attr, value in attrs:
                if attr == "src":
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
    def __init__(self, artist: str, title: str, album: str, url: str, duration: float):
        self.artist = artist
        self.title = title
        self.album = album
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

        songs.append(Song(track_artist, track_title, album, track_url, track_duration))

    # album_playlist = parse_fun(songs)
    return {"art": parser.album_art_url, "songs": songs}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        url = input("Enter album url: ")
    else:
        url = sys.argv[1]

    print(get_songs(url))
