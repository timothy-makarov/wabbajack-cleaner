# Filename: wabbajack_cleaner.py
# Author: Tim Makarov
# Created: 2025-02-01
# Description: Wabbajack Cleaner is a tool for cleaning downloaded mods directory.


__author__ = "Tim Makarov"
__copyright__ = "Copyright 2025, Tim Makarov"
__credits__ = ["Tim Makarov"]
__email__ = "timothy.makarov@gmail.com"
__license__ = "GPL"
__maintainer__ = "Tim Makarov"
__status__ = "Prototype"
__version__ = "0.1.0"


import argparse
import chardet
import configparser
import humanize
import json
import logging
import os
import sys
import zipfile

from datetime import datetime


_name_ = "wabbajack_cleaner"


_ARCH_EXTS = [".7z", ".rar", ".zip"]
_ARGS = None
_DOWNLOADS = None
_LOGGER = None
_MODLIST = None
_MODLIST_JSON = "modlist.json"


def init_logging():
    global _LOGGER

    _LOGGER = logging.getLogger(_name_)
    _LOGGER.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        "{}_{}.log".format(_name_, datetime.now().strftime("%Y%m%d"))
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    _LOGGER.addHandler(file_handler)
    _LOGGER.addHandler(stdout_handler)


def init_args():
    global _ARGS

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        help="Print the version number and exit",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--modlist-path", help="Specifies the path to a Wabbajack modlist file"
    )

    parser.add_argument(
        "--downloads-dir", help="Specifies the Wabbajack directory with downloaded mods"
    )

    parser.add_argument(
        "--dry-run",
        help="Perform analysis without actually deleting files",
        action="store_true",
        default=False,
    )

    _ARGS = parser.parse_args()


def check_args():
    if not _ARGS:
        _LOGGER.error("No arguments were found.")
        sys.exit(1)

    if not _ARGS.modlist_path:
        _LOGGER.error("Modlist path argument was not found: --modlist-path")
        sys.exit(1)

    if not os.path.exists(_ARGS.modlist_path):
        _LOGGER.error("Path does not exist: {}".format(_ARGS.modlist_path))
        sys.exit(1)

    if not _ARGS.downloads_dir:
        _LOGGER.error("Modlist path argument was not found: --downloads-dir")
        sys.exit(1)

    if not os.path.exists(_ARGS.downloads_dir):
        _LOGGER.error("Path does not exist: {}".format(_ARGS.downloads_dir))
        sys.exit(1)


def extract_modlist_json():
    global _MODLIST

    _LOGGER.info("Extracting modlist.json from file: {}".format(_ARGS.modlist_path))

    with zipfile.ZipFile(_ARGS.modlist_path) as zip:
        with open(_MODLIST_JSON, "wb") as file:
            file.write(zip.read("modlist"))

    _LOGGER.info("Validating JSON file: {}".format(_MODLIST_JSON))

    try:
        with open(_MODLIST_JSON, "r") as file:
            modlist = json.load(file)
    except json.JSONDecodeError:
        _LOGGER.error("Failed to read JSON file: {}".format(_MODLIST_JSON))
        sys.exit(1)

    _LOGGER.info("Pretty printing JSON in file: {}".format(_MODLIST_JSON))

    with open(_MODLIST_JSON, "w") as file:
        json.dump(modlist, file, indent=4)

    _LOGGER.info("Analyzing modlist format in file: {}".format(_MODLIST_JSON))

    if "Archives" not in modlist:
        _LOGGER.error(
            'Modlist format error: tag "Archives" was not found in file: {}'.format(
                _MODLIST_JSON
            )
        )
        sys.exit(1)

    _MODLIST = {}
    for archive in modlist["Archives"]:
        if "Name" not in archive:
            _LOGGER.error(
                'Modlist format error: tag "Name" was not found in file: {}; {}'.format(
                    _MODLIST_JSON, str(archive)
                )
            )
            sys.exit(1)

        if archive["Name"] in _MODLIST:
            _LOGGER.error(
                "Duplicate entry found in file: {}; {}".format(
                    _MODLIST_JSON, str(archive)
                )
            )
            sys.exit(1)

        _MODLIST[archive["Name"]] = archive

    modlist_len = len(_MODLIST)
    _LOGGER.info(
        "Found {} mods in modlist file: {}".format(modlist_len, _ARGS.modlist_path)
    )


def get_downloaded_mods():
    global _DOWNLOADS

    _LOGGER.info(
        "Searching for mod archives in directory: {}".format(_ARGS.downloads_dir)
    )

    _DOWNLOADS = {}
    for root, _, files in os.walk(_ARGS.downloads_dir):
        for name in files:
            _, extension = os.path.splitext(name)
            if extension not in _ARCH_EXTS:
                continue
            _DOWNLOADS[name] = {
                "extension": extension,
                "size": os.stat(os.path.join(root, name)).st_size,
                "keep": True,
            }

    total_archs = len(_DOWNLOADS)

    if total_archs == 0:
        _LOGGER.error(
            "No archives were found in directory: {}".format(_ARGS.downloads_dir)
        )
        sys.exit(1)

    _LOGGER.info(
        "Found {} archives in directory: {}".format(total_archs, _ARGS.downloads_dir)
    )


def analyze_installed_mods():
    _LOGGER.info("Analyzing mod list: {}".format(_ARGS.modlist_path))

    without_archive = []
    for name in _MODLIST.keys():
        if name not in _DOWNLOADS:
            archive = _MODLIST[name]

            if "State" in archive:
                if "GameFileSourceDownloader" in str(archive["State"]):
                    continue

            without_archive.append(name)

            _LOGGER.info("Mod without archive: {}".format(archive["Name"]))

    _LOGGER.info("Analyzing downloads directory: {}".format(_ARGS.downloads_dir))

    not_installed = []
    ni_size = 0
    for file in _DOWNLOADS.keys():
        if file not in _MODLIST:
            not_installed.append(file)
            ni_size += _DOWNLOADS[file]["size"]

            _DOWNLOADS[file]["keep"] = False

            meta_fn = os.path.join(_ARGS.downloads_dir, "{}.meta".format(file))

            if os.path.exists(meta_fn):
                try:
                    with open(meta_fn, "rb") as meta_file:
                        meta_enc = chardet.detect(meta_file.read())["encoding"]
                    meta = configparser.ConfigParser()
                    meta.read(meta_fn, encoding=meta_enc)
                except Exception as e:
                    _LOGGER.error(meta_fn)
                    raise e

                _DOWNLOADS[file]["meta_file"] = meta_fn
                _DOWNLOADS[file]["installed"] = (
                    meta.get("General", "installed", fallback="?") == "true"
                )
                _DOWNLOADS[file]["removed"] = (
                    meta.get("General", "removed", fallback="?") == "true"
                )

                _LOGGER.info(
                    "Mod not on the modlist (metadata: installed={}; removed={}): {} ({})".format(
                        _DOWNLOADS[file]["installed"],
                        _DOWNLOADS[file]["removed"],
                        file,
                        humanize.naturalsize(_DOWNLOADS[file]["size"]),
                    )
                )
            else:
                _LOGGER.info("Not installed mod: {}".format(file))

    _LOGGER.info("Mods without archive: {}".format(len(without_archive)))
    _LOGGER.info(
        "Not installed mods: {} ({})".format(
            len(not_installed), humanize.naturalsize(ni_size)
        )
    )


def clean_downloads():
    _LOGGER.info(
        "Cleaning downloads directory (--dry-run={}): {}".format(
            _ARGS.dry_run,
            _ARGS.downloads_dir,
        )
    )

    removed_cnt = 0
    removed_size = 0
    for file in _DOWNLOADS.keys():
        if _DOWNLOADS[file]["keep"]:
            continue
        file_path = os.path.join(_ARGS.downloads_dir, file)
        if _ARGS.dry_run:
            _LOGGER.info(
                "(Not really) Deleting archive: {} ({})".format(
                    file_path, humanize.naturalsize(_DOWNLOADS[file]["size"])
                )
            )
        else:
            _LOGGER.info(
                "Deleting archive: {} ({})".format(
                    file_path, humanize.naturalsize(_DOWNLOADS[file]["size"])
                )
            )
            os.remove(file_path)
        removed_cnt += 1
        removed_size += _DOWNLOADS[file]["size"]

    _LOGGER.info(
        "Removed {} archive files in directory (--dry-run={}): {} ({})".format(
            removed_cnt,
            _ARGS.dry_run,
            _ARGS.downloads_dir,
            humanize.naturalsize(removed_size),
        )
    )


def main():
    init_args()

    if _ARGS.version:
        print(__version__)
        sys.exit(0)

    init_logging()
    check_args()

    t_0 = datetime.now()
    _LOGGER.info("{} {} started".format(_name_, __version__))

    extract_modlist_json()
    get_downloaded_mods()
    analyze_installed_mods()
    clean_downloads()

    t_1 = datetime.now()
    total_seconds = (t_1 - t_0).total_seconds()

    _LOGGER.info(
        "{} {} finished in {:.2f} seconds".format(_name_, __version__, total_seconds)
    )


if __name__ == "__main__":
    main()
