"""Navidrome answers turned into CastHome's models."""

from casthome.subsonic.models import Album


def test_album_keeps_the_names_of_tagged_discs():
    album = Album.from_api(
        {
            "id": "a1",
            "name": "The Fame Monster",
            "discTitles": [
                {"disc": 1, "title": "The Fame Monster", "coverArt": "dc-a1:1"},
                {"disc": 2, "title": "The Fame"},
                {"disc": 3, "title": "  "},
                {"title": "no disc number"},
            ],
        }
    )
    assert album.disc_titles == {1: "The Fame Monster", 2: "The Fame"}
    assert album.model_dump()["disc_titles"] == {1: "The Fame Monster", 2: "The Fame"}


def test_album_without_disc_titles():
    assert Album.from_api({"id": "a1", "name": "One disc"}).disc_titles == {}
