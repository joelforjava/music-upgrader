import subprocess
from pathlib import Path

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from music_upgrader import applescript
from music_upgrader.applescript import (
    GET_TRACK_FIELD,
    SELECT_TRACK_BY_ID,
    SELECT_TRACK_BY_ARTIST_TRACK_NAME_ALBUM,
)


def _run(command: str) -> str:
    resp = subprocess.run(
        ["beet", command],  # TODO - call specific alias, e.g. pbeet, dbeet
        capture_output=True,
    )

    return resp.stdout.decode()


def _get_data_by_id(track_id: str, sub_cmd: str) -> str | int:
    return applescript.run(f"{SELECT_TRACK_BY_ID.format(track_id)}\n{sub_cmd}")


def _get_data_by_fields(
    track_name: str, track_artist: str, track_album: str, sub_cmd: str
) -> str | int:
    return applescript.run(
        f"{SELECT_TRACK_BY_ARTIST_TRACK_NAME_ALBUM.format(track_artist, track_name, track_album)}\n{sub_cmd}"
    )


def get_year(track_id: str):
    return int(_get_data_by_id(track_id, GET_TRACK_FIELD.format("year")))


def _get_year_alt(track_name: str, track_artist: str, track_album: str):
    return int(
        _get_data_by_fields(
            track_name, track_artist, track_album, GET_TRACK_FIELD.format("year")
        )
    )


def is_same_track(old_file: Path | str, new_file: Path | str) -> bool:
    """Verify whether two files represent the same track for a given artist's album.

    Given how this is expected to execute, this could be overkill, but is still an important
    verification that we are currently working with two files that represent the same track
    from a given artist's album.

    Args:
        old_file (Path | str): Path to the old, presumably already in use, file.
        new_file (Path | str): Path to the new file that could potentially replace the old one.

    Returns:
        bool: Whether the two files represent the same track for the same album.
    """
    o = mutagen.File(old_file, easy=True)
    n = mutagen.File(new_file, easy=True)

    # NOTE the use of the list index. If any of these items return nothing, then it'll break
    return (
        o.get("title")[0].lower() == n.get("title")[0].lower()
        and o.get("album")[0].lower() == n.get("album")[0].lower()
        and o.get("artist")[0].lower() == n.get("artist")[0].lower()
    )


def is_upgradable(old_file: Path | str, new_file: Path | str) -> bool:
    o = mutagen.File(old_file)
    n = mutagen.File(new_file)
    if isinstance(o, MP3) and isinstance(n, MP3):
        if n.info.bitrate > o.info.bitrate:
            return True
    elif isinstance(o, MP3) and isinstance(n, FLAC):
        return True
    elif isinstance(o, MP3) and isinstance(n, MP4):
        if n.info.codec.lower() == "alac":
            return True
    return False
