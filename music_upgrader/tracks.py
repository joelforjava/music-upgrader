import subprocess
from pathlib import Path

import mutagen
from inflection import transliterate
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from music_upgrader import applescript
from music_upgrader.applescript import (
    GET_TRACK_FIELD,
    GET_TRACK_INFO,
    LOAD_ALL_FILE_IDS,
    SELECT_TRACK_BY_ARTIST_TRACK_NAME_ALBUM,
    SELECT_TRACK_BY_ID,
    SET_TRACK_FILE_LOCATION,
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


def load_all_ids():
    ids = applescript.run(LOAD_ALL_FILE_IDS)
    return list(map(lambda x: x.strip(), ids.split(",")))
    # return [ii.strip() for ii in ids.split(",")]


def load_all():
    ids = load_all_ids()
    items = []
    for _id in ids:
        info = applescript.run(f"{SELECT_TRACK_BY_ID.format(_id)}\n{GET_TRACK_INFO}")
        items.append((_id, *info.splitlines()))
    return items


def get_year(track_id: str):
    return int(_get_data_by_id(track_id, GET_TRACK_FIELD.format("year")))


def _get_year_alt(track_name: str, track_artist: str, track_album: str):
    return int(
        _get_data_by_fields(
            track_name, track_artist, track_album, GET_TRACK_FIELD.format("year")
        )
    )


def set_file_location(track_id: str, hfs_file_path: str):
    return _get_data_by_id(track_id, SET_TRACK_FILE_LOCATION.format(hfs_file_path))


def is_same_track(old_file: Path | str, new_file: Path | str) -> bool:
    """Verify whether two files represent the same track for a given artist's album.

    Given how this is expected to execute, this could be overkill, but is still an important
    verification that we are currently working with two files that represent the same track
    from a given artist's album.

    However, this may pose a problem given how much beets like to use non-standard keyboard
    characters for single quote and dash, among others.

    This also poses a problem when Beets will normalize a name, e.g. "Song About Nuthin'" becomes
    "Song About Nothing".

    Args:
        old_file (Path | str): Path to the old, presumably already in use, file.
        new_file (Path | str): Path to the new file that could potentially replace the old one.

    Returns:
        bool: Whether the two files represent the same track for the same album.
    """
    o = mutagen.File(old_file, easy=True)
    n = mutagen.File(new_file, easy=True)

    # NOTE the use of the list index. If any of these items return nothing, then it'll break
    try:
        is_same = (
            transliterate(o["title"][0]).lower() == transliterate(n["title"][0]).lower()
            and transliterate(o["album"][0]).lower() == transliterate(n["album"][0]).lower()
            and transliterate(o["artist"][0]).lower() == transliterate(n["artist"][0]).lower()
        )
    except KeyError:
        return False
    return is_same


def get_field_values_from_track(music_track: Path | str, fields: list):
    o = mutagen.File(music_track, easy=True)
    return [o[field][0] for field in fields]


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


if __name__ == "__main__":
    _all = load_all()
    for aa in _all:
        print(aa)
    # print(load_all())
