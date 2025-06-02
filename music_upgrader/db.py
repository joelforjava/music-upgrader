import re
import string
import subprocess
from typing import Union

from beets.dbcore import AndQuery
from beets.dbcore.query import RegexpQuery, StringQuery
from beets.library import Library

from music_upgrader import settings

# ‐
REGEX_REPL = re.compile("[%s]" % re.escape(string.punctuation))

DBS, CMDS = settings.load()

CONFIG_LOC_INDEX = -1


def get_library(db_name):
    return Library(**DBS[db_name])

def regexify(token):
    if not token:
        return token
    f = REGEX_REPL.sub(".?", token)
    s = f[0]
    return f"[{s.upper()}{s.lower()}]{f[1:]}"


class ApiDataService:
    def __init__(self, database_name):
        self.library = get_library(database_name)

    def _execute_query(self, query):
        return self.library.items(query)

    def find_track(self, track_name, track_artist, track_album, track_num=None, search_type=None):
        match search_type:
            case "regex":
                q = AndQuery(
                    subqueries=(
                        RegexpQuery("artist", "^{}$".format(regexify(track_artist))),
                        RegexpQuery("album", "^{}$".format(regexify(track_album))),
                        RegexpQuery("title", "^{}$".format(regexify(track_name))),
                    )
                )
            case "parsed":
                if track_name.endswith("]") or track_name.endswith(")"):
                    start_idx = track_name.find("[")
                    track_name = track_name[:start_idx-1]
                sub_q: list[Union[RegexpQuery, StringQuery]] = [
                    RegexpQuery("artist", "^{}$".format(regexify(track_artist))),
                    RegexpQuery("album", "^{}$".format(regexify(track_album))),
                    RegexpQuery("title", "^{}$".format(regexify(track_name))),
                ]
                if track_num:
                    sub_q.append(StringQuery("track", track_num))
                q = AndQuery(
                    subqueries=(
                        RegexpQuery("artist", "^{}$".format(regexify(track_artist))),
                        RegexpQuery("album", "^{}$".format(regexify(track_album))),
                        RegexpQuery("title", "^{}$".format(regexify(track_name))),
                    )
                )
            case _:
                q = AndQuery(
                    subqueries=(
                        StringQuery("artist", track_artist),
                        StringQuery("album", track_album),
                        StringQuery("title", track_name),
                    )
                )

        resp = self._execute_query(q)
        # if resp.rows:
        #     print("found rows")
        return resp

    def find_all_album_tracks(self, track_artist, track_album):
        resp = self._execute_query(f"artist:'{track_artist}' album:'{track_album}'")
        # if resp.rows:
        #     print("found rows")
        return resp

    def find_album(self, artist, album_name):
        resp = self._execute_query(f"artist:'{artist}' album:'{album_name}'")
        # if resp.rows:
        #     print("found rows")
        return resp

    def load_all(self):
        return self._execute_query(None)


class CliDataService:
    """A CLI-based version of interacting with the beets database.

    This version of the service is intended more for generating ALAC files from existing FLAC
    and for possibly updating entries, namely the original_year. Might just make that part of
    a temporary plugin. Remains to be seen.
    """

    def __init__(self, database_name):
        self.exec = CMDS[database_name]["exec"]
        self.config_loc = self.exec[CONFIG_LOC_INDEX]

    def _execute_query(self, cmd, query=None, fmt=None):
        if fmt:
            args = [*self.exec, cmd, fmt, *query]
        elif query:
            args = [*self.exec, cmd, *query]
        else:
            args = [*self.exec, cmd]

        resp = subprocess.run(
            args,
            capture_output=True,
        )
        if resp.stderr:
            print(resp.stderr.decode("utf-8"))
        return resp.stdout.decode()

    def _execute_get(self, query, fmt=None):
        return self._execute_query("ls", query, fmt)

    def _execute_convert(self, query):
        return self._execute_query("convert", ["-y"] + query)

    def find_track(self, track_name, track_artist, track_album, track_num=None, search_type=None):
        use_regex = search_type == "regex"
        if use_regex:
            query_params = [
                f"artist::^{track_artist}$",
                f"album::^{track_album}$",
                f"title::^{track_name}$",
            ]
        else:
            # NOTE: These commented-out versions were from prior to how query is handled in _execute_query.
            #       It now expects a list
            # resp = self._execute_query(f"{track_artist}")  # NOTE: This works
            # resp = self._execute_query(f"artist:{track_artist}")  # NOTE: THIS works. Note no inner quotes around the query
            # resp = self._execute_query(f"artist:{track_artist} album:{track_album} title:{track_name}")
            # By default, the CLI returns results as "<ARTIST_NAME> - <ALBUM_NAME> - <TRACK_NAME>
            query_params = [
                f"artist:{track_artist}",
                f"album:{track_album}",
                f"title:{track_name}",
            ]
        resp = self._execute_get(query_params)
        # if resp:
        #     print("found rows")
        return resp.splitlines()

    def convert(self, current_beet_path):
        resp = self._execute_convert([f"path:{current_beet_path}"])
        return resp.splitlines()


if __name__ == "__main__":
    test_db_service = False
    if test_db_service:
        db = ApiDataService("physical")
        # db.execute_query_test("title:Stereotype")
        # db.execute_query_test("artist:Meat Puppets album:No Strings Attached")
        # db.execute_query_test("artist:'Powerman 5000' album:Transform")

        # trk_res = db.find_track("Lake of Fire", "Meat Puppets", "No Strings Attached")
        trk_res = db.find_track(
            "Hey, That's Right!", "Powerman 5000", "Transform", search_type="regex"
        )

        if trk_res:
            print(len(trk_res.rows))
            for rr in trk_res.rows:
                print(rr["artist"], rr["album"], rr["title"], rr["albumartist"])

        # trk_res = db.find_track("Hey.? That.?s Right.?", "Powerman 5000", "Transform", use_regex=True)

        # trk_res = db.load_all()
        # if trk_res:
        #     print(len(trk_res.rows))
        #     for rr in trk_res.rows:
        #         print(rr["artist"], rr["album"], rr["title"], rr["albumartist"])

    # NOTE - this doesn't currently work since we run inside a virtualenv that knows nothing about the host installs
    test_cli_service = True
    if test_cli_service:
        db = CliDataService("test")
        trk_res = db.find_track("Lake of Fire", "Meat Puppets", "No Strings Attached")
        if trk_res:
            print(trk_res)
            for rr in trk_res:
                print(rr)

        # conv_resp = db.convert("Lake of Fire", "Meat Puppets", "No Strings Attached")
        # if conv_resp:
        #     print(conv_resp)

        # trk_res = db._execute_query(None)
        # if trk_res:
        #     print(trk_res)
        # for rr in trk_res:
        #     print(rr)
