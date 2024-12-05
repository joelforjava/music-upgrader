import subprocess
from pathlib import Path

LOAD_ALL_PLAY_COUNTS = (
    'tell application "Music" to get {persistent ID, played count} of every track in playlist 1'
)

LOAD_ALL_IDS = 'tell application "Music" to get persistent ID of every track in playlist 1'

LOAD_ALL_FILE_IDS = 'tell application "Music" to get persistent ID of every file track in playlist 1'

SELECT_TRACK_BY_ID = """
    tell application "Music"
        set lib to library playlist 1
        set t to first track whose persistent ID is "{}"
    end tell
"""

SELECT_TRACK_BY_ARTIST_TRACK_NAME_ALBUM = """
    tell application "Music"
        set lib to library playlist 1
        set t to first track whose artist is "{}" and name is "{}" and album is "{}"
    end tell
"""

GET_TRACK_INFO = """
    tell application "Music" to tell t
        set l to ""
        try
            set l to location
            set l to POSIX path of l
        end try
        return track number & "\n" & name & "\n" & artist & "\n" & album & "\n" & album artist & "\n" & year & "\n" & played date as text & "\n" & played count & "\n" & l
    end tell
"""

GET_TRACK_FIELD = """
    tell application "Music" to tell t
        return {} as text
    end tell
"""

SET_TRACK_FILE_LOCATION = """
    tell application "Music" to tell t
        set newLoc to alias "{}"
        set location to newLoc
    end tell
"""
"""NOTE: The location must be an HFS path string"""

SET_TRACK_PLAYED_COUNT = """
    tell application "Music" to tell t
        set played count to {}
    end tell
"""

SET_TRACK_YEAR = """
    tell application "Music" to tell t
        set year to {}
    end tell
"""


def run(command: str) -> str:
    # TODO - make a debug
    # print("Executing command:\n {}".format(command))
    resp = subprocess.run(
        ["osascript", "-e", command],
        capture_output=True,
    )
    if resp.stderr:
        print(resp.stderr.decode("utf-8"))
    return resp.stdout.decode()


def run_script(script_path: Path):
    # TODO - make a debug
    # print("Executing script:\n {}".format(script_path))
    resp = subprocess.run(
        ["osascript", str(script_path)],
        stdout=subprocess.DEVNULL,
    )
    if resp.returncode != 0:
        print(f"Unable to run AppleScript at {script_path}")  # TODO - add logging
        print(resp)
        return False
    return True


def hfs_path_to_posix_path(hfs_path: str) -> str:
    # TODO - double check usage. The new 'load' logic uses POSIX from the beginning
    #        for the Apple Music file location
    tokens = hfs_path.split(":")
    return "/" + "/".join(tokens[1:])


def posix_path_to_hfs_path(posix_path: str) -> str:
    """Convert a POSIX Path to an AppleScript HFS Path.

    The logic used will be greatly simplified and use "Macintosh HD"
    as the drive name. May need to change once on the computer itself.
    """
    drive_name = "Macintosh HD"
    # This currently will cause problems for bands like AC/DC
    # BUT... Beets appears to have been smart enough to not use / in folder names
    return f"{drive_name}{posix_path}".replace("/", ":")


if __name__ == "__main__":
    cmd = f"{SELECT_TRACK_BY_ID.format('61A578F3A06A1801')}\n{GET_TRACK_INFO}"
    print(run(cmd))
