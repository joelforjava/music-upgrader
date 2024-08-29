import csv
import re
import string
from datetime import datetime, timezone
from pathlib import Path

import beets.dbcore.query
from dateutil.parser import ParserError, parse

import applescript as apl
import tracks

from db import ApiDataService


ROOT_LOCATION = "~/Code/Data/Music/Upgrader"


DATE_FORMAT_FOR_FILES = "%Y%m%dT%H%M%SZ"


def read_csv(file_path: Path):
    data = []
    if not file_path.exists():
        print("FILE NOT FOUND")
        return data

    with file_path.open("r") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if "last_played" in row:
                try:
                    row["last_played"] = parse(row["last_played"])
                except ParserError:
                    row["last_played"] = None
            data.append(row)
    return data


def write_csv(data, file_path: Path):
    with file_path.open("x") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


class UpgradeCheck:

    def __init__(self, db: ApiDataService):
        self.db = db

    def process_row(self, csv_row):
        # TODO - verify field names
        row_cpy = csv_row.copy()
        track_artist = csv_row["track_artist"]
        track_title = csv_row["track_name"]
        track_album = csv_row["album"]
        try:
            result = self.db.find_track(track_title, track_artist, track_album)
        except beets.dbcore.query.InvalidQueryError as e:
            regex = re.compile('[%s]' % re.escape(string.punctuation))
            converted = regex.sub('.?', track_title)
            print(e)
            can_upgrade = False
        else:
            can_upgrade = False
            if found := result.get():
                track_location = apl.hfs_path_to_posix_path(csv_row["location"])
                new_file = found["path"].decode("utf-8")
                if tracks.is_same_track(track_location, new_file):
                    print("Verified tracks are same song")
                    can_upgrade = tracks.is_upgradable(track_location, new_file)
                    if can_upgrade:
                        print(f"{track_title} by {track_artist} is upgradable")
                        row_cpy["new_file"] = apl.posix_path_to_hfs_path(new_file)
                else:
                    print("[WARN] files do not contain the same song")
        row_cpy["can_upgrade"] = can_upgrade
        return row_cpy

    def process_csv(self, csv_path: Path):

        data = read_csv(csv_path)

        for_upgrade = []
        no_upgrade = []
        for row in data:
            processed = self.process_row(row)
            if processed["can_upgrade"]:
                for_upgrade.append(processed)
            else:
                print(f'{row} cannot be upgraded')
        return for_upgrade, no_upgrade

    def run(self, csv_path: Path):
        processed, no_upgrade = self.process_csv(csv_path)
        now = datetime.now(timezone.utc)
        out_location = Path(f"{ROOT_LOCATION}/upgrade_checks_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv").expanduser()
        write_csv(processed, out_location)
        noup_location = Path(f"{ROOT_LOCATION}/no_upgrade_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv").expanduser()
        write_csv(no_upgrade, noup_location)


class CopyFilesForUpgrade:
    pass

class ApplyUpgrade:
    pass


def main():
    db = ApiDataService("physical")
    u = UpgradeCheck(db)
    u.run(Path(f"{ROOT_LOCATION}/libraryFiles.csv").expanduser())


if __name__ == "__main__":
    main()
