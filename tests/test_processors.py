import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, create_autospec, mock_open, patch

from music_upgrader import applescript as apl
from music_upgrader.db import CMDS, CliDataService
from music_upgrader.processors import CopyFiles

TEST_CMDS = {"test": {"exe_name": "beet", "exec": ["beet", "-c", "/tmp/beets/config.yaml"]}}


class CopyFilesTests(unittest.TestCase):

    # @patch.dict(CMDS, TEST_CMDS)
    def test_loads_convert_destination_from_yaml_config_file(self):
        dummy_data_file = tempfile.NamedTemporaryFile()
        temp_dir = tempfile.TemporaryDirectory()
        temp_yaml = f"convert:\n  dest: {temp_dir.name}"

        with patch.object(Path, "open", mock_open(read_data=temp_yaml)):
            mock_svc = create_autospec(CliDataService)
            mock_svc.config_loc = "/tmp/beets/config.yaml"
            copy_files = CopyFiles(dummy_data_file.name, mock_svc)
            self.assertEqual(str(copy_files.output_location), temp_dir.name)

    def xtest_copies_file_1(self):
        dummy_data_file = tempfile.NamedTemporaryFile()
        temp_dir = tempfile.TemporaryDirectory()
        temp_yaml = f"convert:\n  dest: {temp_dir.name}"

        o_file = tempfile.NamedTemporaryFile()
        n_file = tempfile.NamedTemporaryFile()

        with patch.object(Path, "open", mock_open(read_data=temp_yaml)):
            mock_svc = create_autospec(CliDataService)
            mock_svc.config_loc = "/tmp/beets/config.yaml"
            copy_files = CopyFiles(dummy_data_file.name, mock_svc)

            csv_row = {
                "new_file": str(Path(temp_dir.name) / "NewFile.mp3"),
                "location": apl.posix_path_to_hfs_path(o_file.name),
            }
            res = copy_files.process_row(csv_row)
            self.assertTrue(res.get("target_existed"))


if __name__ == "__main__":
    unittest.main()
