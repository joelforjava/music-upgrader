import subprocess

import applescript
from applescript import GET_TRACK_FIELD, SELECT_TRACK_BY_ID, SELECT_TRACK_BY_ARTIST_TRACK_NAME_ALBUM


def _run(command: str) -> str:
    resp = subprocess.run(
        [
            "beet",  # TODO - call specific alias, e.g. pbeet, dbeet
            command
        ],
        capture_output=True,
    )

    return resp.stdout.decode()


def _get_data_by_id(track_id: str, sub_cmd: str) -> str | int:
    return applescript.run(f"{SELECT_TRACK_BY_ID.format(track_id)}\n{sub_cmd}")


def _get_data_by_fields(track_name: str, track_artist: str, track_album: str, sub_cmd: str) -> str | int:
    return applescript.run(
        f"{SELECT_TRACK_BY_ARTIST_TRACK_NAME_ALBUM.format(track_artist, track_name, track_album)}\n{sub_cmd}"
    )


def get_year(track_id: str):
    return int(_get_data_by_id(track_id, GET_TRACK_FIELD.format('year')))


def _get_year_alt(track_name: str, track_artist: str, track_album: str):
    return int(_get_data_by_fields(track_name, track_artist, track_album, GET_TRACK_FIELD.format('year')))


if __name__ == "__main__":
    print(get_year('61A578F3A06A1801'))
    print(_get_year_alt("Lake of Fire", "Meat Puppets", "No Strings Attached"))
