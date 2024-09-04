import csv
import re
import string
from datetime import datetime, timezone
from pathlib import Path

import beets.dbcore.query
import yaml
from dateutil.parser import ParserError, parse
from rich.progress import Progress

from . import applescript as apl
from . import tracks
from .db import ApiDataService, CliDataService

ROOT_LOCATION = "~/Code/Data/Music/Upgrader"


DATE_FORMAT_FOR_FILES = "%Y%m%dT%H%M%SZ"

SPACING = " "*len("Checking...")


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

    def __init__(self, db: ApiDataService, enable_file_comparison=False):
        self.db = db
        self.should_compare_files = enable_file_comparison

    def process_row(self, csv_row):
        # TODO - verify field names
        row_cpy = csv_row.copy()
        track_artist = csv_row["track_artist"]
        track_title = csv_row["track_name"]
        track_album = csv_row["album"]
        print(f"Checking... {track_title} by {track_artist} from the album {track_album}")
        can_upgrade = False
        result = None
        for use_regex in False, True:
            try:
                result = self.db.find_track(track_title, track_artist, track_album, use_regex=use_regex)
            except beets.dbcore.query.InvalidQueryError as e:
                # print(e)
                continue
            else:
                if result:
                    break
        else:
            print(SPACING, "Track not found")
        if result:
            can_upgrade = False
            if found := result.get():
                track_location = apl.hfs_path_to_posix_path(csv_row["location"])
                new_file = found["path"].decode("utf-8")
                if self.should_compare_files:
                    if tracks.is_same_track(track_location, new_file):
                        print(SPACING, "Verified tracks are same song")
                        can_upgrade = tracks.is_upgradable(track_location, new_file)
                        if can_upgrade:
                            print(SPACING, "is upgradable")
                            row_cpy["new_file"] = apl.posix_path_to_hfs_path(new_file)
                        else:
                            print(SPACING, "cannot be upgraded")
                    else:
                        print(SPACING, "[WARN] files do not contain the same song")
                else:
                    can_upgrade = tracks.is_upgradable(track_location, new_file)
                    if can_upgrade:
                        print(SPACING, "is upgradable")
                        row_cpy["new_file"] = apl.posix_path_to_hfs_path(new_file)
                    else:
                        print(SPACING, "cannot be upgraded")
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
                no_upgrade.append(processed)
        return for_upgrade, no_upgrade

    def run(self, csv_path: Path):
        # with Progress() as progress:
        #     pass
        processed, no_upgrade = self.process_csv(csv_path)
        now = datetime.now(timezone.utc)
        out_location = Path(f"{ROOT_LOCATION}/upgrade_checks_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv").expanduser()
        write_csv(processed, out_location)
        noup_location = Path(f"{ROOT_LOCATION}/no_upgrade_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv").expanduser()
        if no_upgrade:
            write_csv(no_upgrade, noup_location)


class CopyFilesForUpgrade:
    """
    Copy files from the 'upgrade checks' CSV new_file values.
    If the destination already exists, back up the file before copying the new file!
    This will mostly be relevant for MP3 files being replaced by higher quality MP3 files.

    This simply copies the files over. It does not call any AppleScript!
    """

    def __init__(self, service: CliDataService):
        self.service = service
        with Path(self.service.config_loc).expanduser().open() as config_file:
            self.output_location = Path(
                yaml.load(config_file, Loader=yaml.SafeLoader)["convert"]["dest"]
            ).expanduser()
        # assert self.output_location.exists()

    def process_row(self, csv_row):
        # TODO - we need to convert FLACs to ALAC. If MP3, just copy the file from "new_file" to new location

        # FLAC to ALAC flow
        row_cpy = csv_row.copy()
        track_artist = csv_row["track_artist"]
        track_title = csv_row["track_name"]
        track_album = csv_row["album"]
        new_file_source = apl.hfs_path_to_posix_path(csv_row["new_file"])
        print(f"Upgrading... {track_title} by {track_artist} from the album {track_album}")
        self.service.convert(track_title, track_artist, track_album)
        p = Path(new_file_source).with_suffix(".m4a")
        # TODO - might be better to use the artist/album values from the source file itself
        expected_output = self.output_location / "FLAC" / track_artist / track_album / p.name
        print(expected_output)
        assert expected_output.exists()
        # TODO - Once output, copy file to new destination, e.g ~/Music
        row_cpy["new_file"] = str(expected_output)
        return row_cpy

    def process_csv(self, csv_path: Path):

        data = read_csv(csv_path)

        results = []
        for row in data:
            processed = self.process_row(row)
            results.append(processed)
        return results

    def run(self, csv_path: Path):
        # with Progress() as progress:
        #     pass
        processed = self.process_csv(csv_path)
        now = datetime.now(timezone.utc)
        out_location = Path(f"{ROOT_LOCATION}/copy_results{now.strftime(DATE_FORMAT_FOR_FILES)}.csv").expanduser()
        write_csv(processed, out_location)


class ApplyUpgrade:
    """
    Applies the update by calling AppleScript and telling it to replace the file
    reference with the new file, copied from the CopyFilesForUpgrade step.
    """
    pass


def main():
    db = ApiDataService("physical")
    u = UpgradeCheck(db)
    u.run(Path(f"{ROOT_LOCATION}/libraryFiles.csv").expanduser())


if __name__ == "__main__":
    main()
