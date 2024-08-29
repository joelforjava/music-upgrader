import subprocess
from beets.library import Library, Item


DBS = {
    "physical": {
        "path": "/Users/joel/Music/Beets/main/musiclibrary.db",
        "directory": "/Users/joel/Music/Beets/main",
        "path_formats": (
            ("default", "$format/$albumartist/$album%aunique{}/$track - $title"),
            ("singleton", "$format/Non-Album/$artist/$title"),
            ("comp", "$format/Compilations/$album%aunique{}/$track - $title"),
            ("albumtype:soundtrack", "$format/Soundtracks/$album/$track $title}"),
        )
    }
}
# TODO - migrate to external config. read this back from the YAML

CMDS = {
    "physical": {
        "exe_name": "pbeet"
    },
    "digital": {
        "exe_name": "dbeet"
    },
    "test": {
        "exe_name": "beet",
        "exec": ["beet", "-c", "/Users/joel/.config/beets/config.yaml"]
        # "exe_name": "beet -c /Users/joel/.config/beets/config.yaml"
    }
}
# NOTE: Could alternately use the full beet -c config_file.yaml instead of alias name


def get_library(db_name):
    return Library(**DBS[db_name])


class ApiDataService:
    def __init__(self, database_name):
        self.library = get_library(database_name)

    def _execute_query(self, query):
        return self.library.items(query)

    def find_track(self, track_name, track_artist, track_album, use_regex=False):
        if use_regex:
            resp = self._execute_query(f"artist::'^{track_artist}$' album::'^{track_album}$' title::'^{track_name}$'")
        else:
            resp = self._execute_query(f"artist:'{track_artist}' album:'{track_album}' title:'{track_name}'")
        if resp.rows:
            print("found rows")
        return resp

    def find_all_album_tracks(self, track_artist, track_album):
        resp = self._execute_query(f"artist:'{track_artist}' album:'{track_album}'")
        if resp.rows:
            print("found rows")
        return resp

    def find_album(self, artist, album_name):
        resp = self._execute_query(f"artist:'{artist}' album:'{album_name}'")
        if resp.rows:
            print("found rows")
        return resp

    def load_all(self):
        return self._execute_query(None)


class CliDataService:
    """ A CLI-based version of interacting with the beets database.

    This version of the service is intended more for generating ALAC files from existing FLAC
    and for possibly updating entries, namely the original_year. Might just make that part of
    a temporary plugin. Remains to be seen.
    """
    def __init__(self, database_name):
        self.cmd = CMDS[database_name]["exe_name"]

    def _execute_query(self, query, fmt=None):
        if fmt:
            args = [self.cmd, "ls", fmt, query]
        elif query:
            args = [self.cmd, "ls", *query]
        else:
            args = [self.cmd, "ls"]

        resp = subprocess.run(
            args,
            capture_output=True,
        )
        if resp.stderr:
            print(resp.stderr.decode("utf-8"))
        return resp.stdout.decode()

    def find_track(self, track_name, track_artist, track_album, use_regex=False):
        if use_regex:
            resp = self._execute_query(f"'artist::^{track_artist}$' 'album::^{track_album}$' 'title::^{track_name}$'")
        else:
            # NOTE: These commented-out versions were from prior to how query is handled in _execute_query.
            #       It now expects a list
            # resp = self._execute_query(f"{track_artist}")  # NOTE: This works
            # resp = self._execute_query(f"artist:{track_artist}")  # NOTE: THIS works. Note no inner quotes around the query
            # resp = self._execute_query(f"artist:{track_artist} album:{track_album} title:{track_name}")
            # By default, the CLI returns results as "<ARTIST_NAME> - <ALBUM_NAME> - <TRACK_NAME>
            resp = self._execute_query([f"artist:{track_artist}", f"album:{track_album}", f"title:{track_name}"])
        if resp:
            print("found rows")
        return resp.splitlines()


if __name__ == "__main__":
    test_db_service = False
    if test_db_service:
        db = ApiDataService("physical")
        # db.execute_query_test("title:Stereotype")
        # db.execute_query_test("artist:Meat Puppets album:No Strings Attached")
        # db.execute_query_test("artist:'Powerman 5000' album:Transform")

        trk_res = db.find_track("Lake of Fire", "Meat Puppets", "No Strings Attached")

        if trk_res:
            print(len(trk_res.rows))
            for rr in trk_res.rows:
                print(rr["artist"], rr["album"], rr["title"], rr["albumartist"])

        # trk_res = db.find_track("Hey.? That.?s Right.?", "Powerman 5000", "Transform", use_regex=True)

        trk_res = db.load_all()
        if trk_res:
            print(len(trk_res.rows))
            for rr in trk_res.rows:
                print(rr["artist"], rr["album"], rr["title"], rr["albumartist"])

    # NOTE - this doesn't currently work since we run inside a virtualenv that knows nothing about the host installs
    test_cli_service = True
    if test_cli_service:
        db = CliDataService("test")
        trk_res = db.find_track("Lake of Fire", "Meat Puppets", "No Strings Attached")
        if trk_res:
            print(trk_res)
            for rr in trk_res:
                print(rr)
        # trk_res = db._execute_query(None)
        # if trk_res:
        #     print(trk_res)
            # for rr in trk_res:
            #     print(rr)
