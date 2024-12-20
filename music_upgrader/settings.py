import configparser
import json
import logging.config
import os
from collections import defaultdict
from pathlib import Path

import yaml


config = configparser.ConfigParser(delimiters=["="])

_conf_paths = map(lambda x: Path(x) / "config.ini", [
    Path.cwd(),
    Path.home() / ".config" / "music_upgrader",
    Path(__file__).parent.parent,  # This is meant to be the file in the local code repo
    Path(os.environ.get("MUSIC_UPGRADER_CONF", __file__)),  # Need a good default. Can't leave None or there'll be an error
])

config.read(_conf_paths)

try:
    logging.config.dictConfig(json.loads(Path(config["DEFAULT"]["logging_config_loc"]).read_text()))
except (IOError, KeyError):
    # TODO - set NullHandler?
    # Not sure KeyError should be caught... we WANT there to be some sort of default!
    pass

LOG = logging.getLogger(__name__)

EXPECTED_KEYS = ["path", "directory", "path_formats"]


def load():
    dbs = {}
    cmds = defaultdict(dict)
    avail = config.get("library", "names", fallback="").split(",")
    for ll in avail:
        if not ll:
            continue
        LOG.debug("Loading %s", ll)
        config_items = config[f"library.{ll}"]
        LOG.debug("Path: %s", config_items["path"])
        tmp = dict(config_items)
        if "config_file" in config_items:
            with Path(config_items["config_file"]).open() as f:
                yaml_config = yaml.safe_load(f)
            tmp["path_formats"] = tuple(yaml_config["paths"].items())
        else:
            tmp["path_formats"] = tuple(config.items(f"library.{ll}.formats"))

        cmds[ll]["exec"] = config_items["exec"].split()
        dbs[ll] = {}
        for k in tmp.keys():
            # Cannot deviate from EXPECTED_KEYS due to how the Beets Library is instantiated
            if k in EXPECTED_KEYS:
                dbs[ll][k] = tmp[k]

    LOG.info("Loaded %s databases: %s", len(dbs.keys()), dbs.keys())
    return dbs, cmds


if __name__ == "__main__":
    load()
