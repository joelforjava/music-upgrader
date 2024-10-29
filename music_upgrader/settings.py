import configparser
import json
import logging
import logging.config
from pathlib import Path

import yaml


# TODO - figure out how to make this dynamic
SETTINGS_PATH = Path(__file__).parent.parent / 'config.ini'

config = configparser.ConfigParser(delimiters=["="])
config.read(SETTINGS_PATH)

logging.config.dictConfig(json.loads(Path(config["DEFAULT"]["logging_config_name"]).read_text()))


EXPECTED_KEYS = ["path", "directory", "path_formats"]


def load_db_info():
    dbs = {}
    avail = config["library"]["names"].split(",")
    for ll in avail:
        print("Loading {}".format(ll))
        config_items = config[f"library.{ll}"]
        print(config_items["path"])
        tmp = dict(config_items)
        if "config_file" in config_items:
            with Path(config_items["config_file"]).open() as f:
                yaml_config = yaml.safe_load(f)
            tmp["path_formats"] = tuple(yaml_config["paths"].items())
        else:
            tmp["path_formats"] = tuple(config.items(f"library.{ll}.formats"))

        dbs[ll] = {}
        for k in tmp.keys():
            if k in EXPECTED_KEYS:
                dbs[ll][k] = tmp[k]

    # print(json.dumps(dbs, indent=2))
    print(dbs)
    return dbs


if __name__ == "__main__":
    load_db_info()
