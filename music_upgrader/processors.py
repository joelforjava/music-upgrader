import concurrent.futures
import csv
import logging
import subprocess
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path
from typing import Final, Optional

import beets.dbcore.query
import mutagen
import yaml
from dateutil.parser import ParserError, parse
from rich.progress import Progress

from . import applescript as apl
from . import tracks
from .db import ApiDataService, CliDataService

ROOT_LOCATION = "~/Code/Data/Music/Upgrader"
"""Root location of the data files used for processing"""

MODULE_PATH = (Path(__file__) / "..").resolve()
"""The root path of the module"""

DATE_FORMAT_FOR_FILES = "%Y%m%dT%H%M%SZ"
"""Date format to use when saving files"""

SPACING = " " * len("Checking...")
"""Spacing used to format output"""

CSV_HEADER = ("persistent_id", "track_number", "track_name", "track_artist", "album", "album_artist", "track_year", "last_played", "play_count", "location")

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


class LoadLatestLibrary:
    def __init__(self, script_path: Path, data_path: Path):
        self.script_path = script_path
        self.data_path = data_path

    def run(self):
        if self.data_path.exists():
            print("Backing up previous data file...")
            now = datetime.now(timezone.utc)
            self.data_path.rename(
                self.data_path.with_stem(
                    f"{self.data_path.stem}_{now.strftime(DATE_FORMAT_FOR_FILES)}"
                )
            )
        ids = tracks.load_all_ids()
        num_ids = len(ids)
        with Progress() as progress:

            def _get_track_info(track_id):
                track_info = apl.run(f"{apl.SELECT_TRACK_BY_ID.format(track_id)}\n{apl.GET_TRACK_INFO}")
                if not progress.finished:
                    progress.update(main_task, advance=1)
                return track_id, *track_info.splitlines()

            main_task = progress.add_task("Collecting Library Details...", total=num_ids)
            with ThreadPoolExecutor(max_workers=8) as pool:
                items = sorted(pool.map(_get_track_info, ids), key=lambda x: (x[3], x[4], int(x[1])))

        with self.data_path.open("w") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(CSV_HEADER)
            writer.writerows(items)
        return items


class BaseProcess:
    def __init__(self, data_file):
        self.data_path = Path(data_file)
        # TODO - set up logger to be on the class name
        # TODO TODO - configure
        self.logger = logging.getLogger(__name__)

    def process_row(self, csv_row):
        raise NotImplementedError

    def process_csv(self):

        data = read_csv(self.data_path)
        self.logger.info("Read data file: %s", self.data_path)
        results = []
        for row in data:
            processed = self.process_row(row)
            results.append(processed)
        return results

    def process_csv_v2(self):
        data = read_csv(self.data_path)
        self.logger.info("Read data file: %s", self.data_path)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = sorted(pool.map(self.process_row, data), key=lambda x: (x[3], x[4], int(x[1])))
        return results

    def run(self):
        # with Progress() as progress:
        #     pass
        processed = self.process_csv()
        now = datetime.now(timezone.utc)
        file_name = f"{self.data_path.stem}_results_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv"
        out_location = Path(f"{ROOT_LOCATION}/{file_name}").expanduser()
        write_csv(processed, out_location)
        self.logger.info("Wrote results to %s", out_location)


class UpgradeCheck(BaseProcess):

    def __init__(self, data_file, db: ApiDataService, enable_file_comparison=False):
        super().__init__(data_file)
        self.db = db
        self.should_compare_files = enable_file_comparison
        self.logger.info("Initialized. Will compare files? - %s", enable_file_comparison)

    def process_row(self, csv_row):
        row_cpy = csv_row.copy()
        track_artist = csv_row["track_artist"]
        track_title = csv_row["track_name"]
        track_album = csv_row["album"]
        self.logger.info("Processing: '%s' by %s from the album '%s'", track_title, track_artist, track_album)
        if result := self.check_for_track(track_title, track_artist, track_album):
            found = result.get()
            new_file = found["path"].decode("utf-8")
            upgrade_reason = self.determine_upgrade_status(csv_row["location"], new_file, self.should_compare_files)
            can_upgrade = upgrade_reason in ["BETTER_QUALITY"]
            if can_upgrade:
                self.logger.info("\tthis track will be upgraded due to: %s", upgrade_reason)
                row_cpy["new_file"] = new_file
                row_cpy["b_id"] = found["id"]
                row_cpy["b_original_year"] = found["original_year"]
                row_cpy["b_year"] = found["year"]
                row_cpy["year_action"] = "itunes_year"
            else:
                self.logger.info("\tthis track will not be upgraded. Reason: %s", upgrade_reason)
        else:
            upgrade_reason = "NOT_FOUND"
            can_upgrade = False
            self.logger.info("\tthis track was not found in the database")
        row_cpy["upgrade_reason"] = upgrade_reason
        row_cpy["can_upgrade"] = can_upgrade
        return row_cpy

    @staticmethod
    def determine_upgrade_status(current_track_location, proposed_track, should_compare_file_tags) -> str:

        def _is_upgradable(_curr, _new):
            if tracks.is_upgradable(_curr, _new):
                return "BETTER_QUALITY"
            else:
                return "SAME_QUALITY"

        if should_compare_file_tags:
            if tracks.is_same_track(current_track_location, proposed_track):
                return _is_upgradable(current_track_location, proposed_track)
            else:
                return "DO_NOT_MATCH"
        else:
            return _is_upgradable(current_track_location, proposed_track)

    def check_for_track(self, track_title, track_artist, track_album):
        """Look for the file within the selected beets library"""
        result = None
        for use_regex in False, True:
            try:
                self.logger.info("Querying API. Using Regex? %s", use_regex)
                result = self.db.find_track(
                    track_title, track_artist, track_album, use_regex=use_regex
                )
            except beets.dbcore.query.InvalidQueryError as e:
                self.logger.exception("Invalid query provided to beets API.")
                continue
            else:
                if result:
                    self.logger.debug("Found match. Regex used? %s", use_regex)
                    break
        else:
            print(SPACING, "Track not found")
            self.logger.warning("Track not found: %s by %s", track_title, track_artist)
        return result

    def process_csv(self):

        data = read_csv(self.data_path)

        for_upgrade = []
        no_upgrade = []
        for row in data:
            processed = self.process_row(row)
            if processed["can_upgrade"]:
                for_upgrade.append(processed)
            else:
                no_upgrade.append(processed)
        return for_upgrade, no_upgrade

    def process_csv_v2(self):
        data = read_csv(self.data_path)
        self.logger.info("Read data file: %s", self.data_path)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = sorted(pool.map(self.process_row, data), key=lambda x: (x[3], x[4], int(x[1])))

        grouped = groupby(results, key=lambda x: x["can_upgrade"])
        return results

    def run(self):
        # with Progress() as progress:
        #     pass
        processed, no_upgrade = self.process_csv()
        now = datetime.now(timezone.utc)
        out_location = Path(
            f"{ROOT_LOCATION}/upgrade_checks_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv"
        ).expanduser()
        write_csv(processed, out_location)
        self.logger.info("Saving: %s", out_location)
        noup_location = Path(
            f"{ROOT_LOCATION}/no_upgrade_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv"
        ).expanduser()
        if no_upgrade:
            write_csv(no_upgrade, noup_location)
            self.logger.info("Saving: %s", noup_location)


class CopyFiles(BaseProcess):
    """
    Copy files from the 'upgrade checks' CSV new_file values.
    If the destination already exists, back up the file before copying the new file!
    This will mostly be relevant for MP3 files being replaced by higher quality MP3 files.

    This simply copies the files over. It does not call any AppleScript!
    """

    def __init__(self, data_file, service: CliDataService):
        super().__init__(data_file)
        self.service = service

    def process_row(self, csv_row):
        """Process a row for copying the intended new file to the music library location.

        Copy the intended new file to the music library location.
        """

        row_cpy = csv_row.copy()
        file_to_copy = Path(csv_row["new_file"])

        original_track_path = Path(csv_row["location"])
        self.logger.info("Replacing '%s' with '%s'", original_track_path, file_to_copy)
        original_parent = original_track_path.parent
        target_path = original_parent / file_to_copy.name
        self.logger.info("\tTarget path: %s", target_path)
        target_exists = False
        if target_path.is_dir():
            raise ValueError("\tTarget should not be a directory!")
        if target_path.exists():
            target_exists = True
            backup_target = target_path.with_suffix(".bak")
            target_path.rename(backup_target)
            self.logger.info("\tBacking up previous file found at target")
        file_to_copy.rename(target_path)
        self.logger.info("\tFile move complete")

        row_cpy["new_file"] = str(target_path)
        row_cpy["target_existed"] = target_exists
        return row_cpy


class ConvertFiles(BaseProcess):
    """
    Copy files from the 'upgrade checks' CSV new_file values.
    If the destination already exists, back up the file before copying the new file!
    This will mostly be relevant for MP3 files being replaced by higher quality MP3 files.

    If a higher quality file is a FLAC file, it will be converted to ALAC and this converted file will be used instead.

    This simply copies the files over. It does not call any AppleScript!
    """

    def __init__(self, data_file, service: CliDataService):
        super().__init__(data_file)
        self.service = service
        with Path(self.service.config_loc).expanduser().open() as config_file:
            self.output_location = Path(
                yaml.load(config_file, Loader=yaml.SafeLoader)["convert"]["dest"]
            ).expanduser()
        # assert self.output_location.exists()
        self.logger.info("ConvertFiles initialized. Outputting files to %s", self.output_location)

    def process_row(self, csv_row):
        """Process a row for copying the intended new file to the music library location.

        Copy the intended new file to the staging location. If the new file is a FLAC file,
        it will be converted to ALAC and this converted file will be used instead.
        """
        track_artist = csv_row["track_artist"]
        track_title = csv_row["track_name"]
        track_album = csv_row["album"]

        def _convert_track():
            """Convert a FLAC file to ALAC, which stages the file to a new location."""
            self.logger.info("Converting... '%s' by %s from the album", track_title, track_artist, track_album)
            self.service.convert_2(new_file_path)
            self.logger.info("Conversion complete")
            parts = new_file_path.parts
            t = list(parts[parts.index("FLAC"):])
            return self.output_location.joinpath(*t).with_suffix(".m4a")

        self.logger.info("Processing %s by %s from the album %s", track_title, track_artist, track_album)
        row_cpy = csv_row.copy()
        new_file_source = csv_row["new_file"]
        new_file_path: Final[Path] = Path(new_file_source)
        if (
            new_file_path.suffix.lower() == ".flac"
        ):  # Could use Mutagen for this, but seems a bit overkill
            self.logger.info("Converting FLAC file to ALAC")
            file_to_copy = _convert_track()
            if not file_to_copy.exists():
                # TODO - how do we handle this from a flow perspective? Should everything halt?
                #        At the very least, should log the error in the row. Perhaps "success"?
                raise ValueError(f"Could not find converted file - {str(file_to_copy)}")
            else:
                print(SPACING, "New file located at", str(file_to_copy))
                self.logger.info("New file located at: %s", str(file_to_copy))
        else:
            # FLAC files are the only files that are converted to a different format. The others
            # should be copied from the original directory to prevent the later process from moving
            # the original files that belong to Beets.
            print(f"Copying... {track_title} by {track_artist} from the album {track_album}")
            new_file_name = new_file_path.name
            new_file_stem = new_file_path.stem
            self.logger.info("Copying %s file to staging location", new_file_stem[1:].upper())
            file_ext = new_file_name.split(".")[-1]
            dest_root_dir = self.output_location / file_ext.upper()
            if not dest_root_dir.exists():
                dest_root_dir.mkdir(parents=True)
                self.logger.debug("Created %s Destination directory", file_ext.upper())

            _parts = new_file_path.parts
            _sub_parts = list(_parts[_parts.index(file_ext.upper())+1:])
            track_path = dest_root_dir.joinpath(*_sub_parts)

            if not track_path.parent.exists():
                track_path.parent.mkdir(parents=True, exist_ok=True)
                self.logger.debug("Created album directory")
            track_path.write_bytes(new_file_path.read_bytes())

            file_to_copy = track_path

        # Apple Music/iTunes has no concept of 'original release year', so the 'year' field
        # must be set in order to segment tracks into particular years, decades, etc.

        # Choices are: nothing, b_original_year, b_year, itunes_year
        year_action = csv_row.get("year_action", "nothing")
        self.logger.info("Updating year using %s action", year_action)
        match year_action.lower():
            case "b_original_year":
                new_track_year = csv_row["b_original_year"]
            case "b_year":
                new_track_year = csv_row["b_year"]
            case "itunes_year":
                new_track_year = csv_row["track_year"]
            case _:
                new_track_year = csv_row["track_year"]

        current_year = csv_row["track_year"]
        if current_year != new_track_year:
            self.logger.info(
                "Updating year value from %s to %s as per year action: %s",
                current_year,
                new_track_year,
                year_action
            )
            o = mutagen.File(file_to_copy, easy=True)
            # This could result in a loss of fidelity since this replaces a potential full date, e.g. 1999-01-01
            # with just a year value.
            o["date"] = new_track_year
            o.save()

        row_cpy["new_file"] = str(file_to_copy)
        return row_cpy


class ApplyUpgrade(BaseProcess):
    """
    Applies the update by calling AppleScript and telling it to replace the file
    reference with the new file, copied from the CopyFilesForUpgrade step.
    """

    def __init__(self, data_file):
        super().__init__(data_file)

    def process_row(self, csv_row):
        row_cpy = csv_row.copy()
        persistent_id = csv_row["persistent_id"]
        new_file = apl.posix_path_to_hfs_path(csv_row["new_file"])
        original_track_path = Path(csv_row["location"])
        original_track_path.unlink(missing_ok=True)
        try:
            self.logger.info("Setting new file location for track with persistent ID %s", persistent_id)
            # TODO - delete old file prior to calling applescript! Otherwise, Apple Music/iTunes will
            #        rename the new files in unexpected ways. Not the biggest deal, but it'll make removal
            #        later more difficult
            tracks.set_file_location(persistent_id, new_file)
        except subprocess.SubprocessError:
            self.logger.exception("Could not update track")
            row_cpy["success"] = False
        else:
            self.logger.info("Update complete")
            row_cpy["new_file"] = new_file
            row_cpy["success"] = True
        return row_cpy


def main():
    db = ApiDataService("physical")
    p = Path(f"{ROOT_LOCATION}/libraryFiles.csv").expanduser()
    u = UpgradeCheck(p, db)
    u.run()


if __name__ == "__main__":
    main()
