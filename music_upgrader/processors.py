import csv
import subprocess
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


class BaseProcess:
    def __init__(self, data_file):
        self.data_path = Path(data_file)

    def process_row(self, csv_row):
        raise NotImplementedError

    def process_csv(self):

        data = read_csv(self.data_path)

        results = []
        for row in data:
            processed = self.process_row(row)
            results.append(processed)
        return results


class UpgradeCheck(BaseProcess):

    def __init__(self, data_file, db: ApiDataService, enable_file_comparison=False):
        super().__init__(data_file)
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
                row_cpy["b_id"] = found["id"]
                row_cpy["b_original_year"] = found["original_year"]
                row_cpy["b_year"] = found["year"]
        row_cpy["can_upgrade"] = can_upgrade
        return row_cpy

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

    def run(self):
        # with Progress() as progress:
        #     pass
        processed, no_upgrade = self.process_csv()
        now = datetime.now(timezone.utc)
        out_location = Path(f"{ROOT_LOCATION}/upgrade_checks_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv").expanduser()
        write_csv(processed, out_location)
        noup_location = Path(f"{ROOT_LOCATION}/no_upgrade_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv").expanduser()
        if no_upgrade:
            write_csv(no_upgrade, noup_location)


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
        with Path(self.service.config_loc).expanduser().open() as config_file:
            self.output_location = Path(
                yaml.load(config_file, Loader=yaml.SafeLoader)["convert"]["dest"]
            ).expanduser()
        # assert self.output_location.exists()

    def process_row(self, csv_row):
        """Process a row for copying the intended new file to the music library location.

        Copy the intended new file to the music library location. If the new file is a FLAC file,
        it will be converted to ALAC and this converted file will be used instead.
        """

        row_cpy = csv_row.copy()
        new_file_source = csv_row["new_file"]
        file_to_copy = Path(new_file_source)

        original_track_path = Path(apl.hfs_path_to_posix_path(csv_row["location"]))
        print(SPACING, f"Replacing {original_track_path} with {file_to_copy}")
        original_parent = original_track_path.parent
        target_path = original_parent / file_to_copy.name
        target_exists = False
        if target_path.is_dir():
            print(SPACING, f"Expected target is: {target_path}")
            raise ValueError("Target should not be a directory!")
        if target_path.exists():
            target_exists = True
            backup_target = target_path.with_suffix(".bak")
            target_path.rename(backup_target)
            print(SPACING, "Backing up existing file")
        print(SPACING, "Moving file", str(file_to_copy))
        file_to_copy.rename(target_path)
        print(SPACING, "         to", str(target_path))

        row_cpy["new_file"] = str(target_path)
        row_cpy["target_existed"] = target_exists
        return row_cpy

    def run(self):
        # with Progress() as progress:
        #     pass
        processed = self.process_csv()
        now = datetime.now(timezone.utc)
        file_name = f"{self.data_path.stem}_results_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv"
        out_location = Path(f"{ROOT_LOCATION}/{file_name}").expanduser()
        write_csv(processed, out_location)



class ConvertFiles(BaseProcess):
    """
    Copy files from the 'upgrade checks' CSV new_file values.
    If the destination already exists, back up the file before copying the new file!
    This will mostly be relevant for MP3 files being replaced by higher quality MP3 files.

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

    def process_row(self, csv_row):
        """Process a row for copying the intended new file to the music library location.

        Copy the intended new file to the staging location. If the new file is a FLAC file,
        it will be converted to ALAC and this converted file will be used instead.
        """
        track_artist = csv_row["track_artist"]
        track_title = csv_row["track_name"]
        track_album = csv_row["album"]

        should_copy_year_from_db = csv_row.get("copy_year", False)

        def _convert_track():
            print(f"Converting... {track_title} by {track_artist} from the album {track_album}")
            # TODO - rethink regex. If you use regex, it'll expect all of these values to be exact
            #        so, disabled it for now. Likely will need to do a loop like for checks
            self.service.convert(track_title, track_artist, track_album, use_regex=False)
            p = new_file_path.with_suffix(".m4a")
            # TODO - might be better to use the artist/album values from the source file itself
            # TODO TODO - also want to copy "original_year" to the "year" field. This might need to
            #             be done regardless of whether we are working with FLAC files.
            return self.output_location / "FLAC" / track_artist / track_album / p.name

        row_cpy = csv_row.copy()
        new_file_source = apl.hfs_path_to_posix_path(csv_row["new_file"])
        new_file_path = Path(new_file_source)
        if new_file_path.suffix.lower() == ".flac":  # Could use Mutagen for this, but seems a bit overkill
            file_to_copy = _convert_track()
            if not file_to_copy.exists():
                print(SPACING, "Could not find converted file -", str(file_to_copy))
                # TODO - how do we handle this from a flow perspective? Should everything halt?
                #        At the very least, should log the error in the row. Perhaps "success"?
                raise ValueError(f"Could not find converted file - {str(file_to_copy)}")
        else:
            # FLAC files are the only files that are converted to a different format. The others
            # should be copied from the original directory to prevent the later process from moving
            # the original files that belong to Beets.
            print(f"Copying... {track_title} by {track_artist} from the album {track_album}")
            new_file_name = new_file_path.name
            file_ext = new_file_name.split(".")[-1]
            dest_root_dir = self.output_location / file_ext.upper()
            if not dest_root_dir.exists():
                dest_root_dir.mkdir(parents=True)
                print(SPACING, f"Created {file_ext.upper()} Destination directory")

            track_dir = dest_root_dir / csv_row["album_artist"] / track_album
            if not track_dir.exists():
                track_dir.mkdir(parents=True)
                print(SPACING, f"Created album directory")
            track_path = track_dir / new_file_name
            track_path.write_bytes(new_file_path.read_bytes())

            file_to_copy = track_path

        row_cpy["new_file"] = str(file_to_copy)
        return row_cpy

    def run(self):
        # with Progress() as progress:
        #     pass
        processed = self.process_csv()
        now = datetime.now(timezone.utc)
        file_name = f"{self.data_path.stem}_results_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv"
        out_location = Path(f"{ROOT_LOCATION}/{file_name}").expanduser()
        write_csv(processed, out_location)


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
        original_track_path = Path(apl.hfs_path_to_posix_path(csv_row["location"]))
        original_track_path.unlink(missing_ok=True)
        try:
            # TODO - delete old file prior to calling applescript! Otherwise, Apple Music/iTunes will
            #        rename the new files in unexpected ways. Not the biggest deal, but it'll make removal
            #        later more difficult
            tracks.set_file_location(persistent_id, new_file)
        except subprocess.SubprocessError:
            row_cpy["success"] = False
        else:
            row_cpy["new_file"] = new_file
            row_cpy["success"] = True
        return row_cpy

    def run(self):
        # with Progress() as progress:
        #     pass
        processed = self.process_csv()
        now = datetime.now(timezone.utc)
        file_name = f"{self.data_path.stem}_results_{now.strftime(DATE_FORMAT_FOR_FILES)}.csv"
        out_location = Path(f"{ROOT_LOCATION}/{file_name}").expanduser()
        write_csv(processed, out_location)


def main():
    db = ApiDataService("physical")
    p = Path(f"{ROOT_LOCATION}/libraryFiles.csv").expanduser()
    u = UpgradeCheck(p, db)
    u.run()


if __name__ == "__main__":
    main()
