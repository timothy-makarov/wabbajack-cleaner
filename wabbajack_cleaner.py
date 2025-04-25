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
__version__ = "0.2.0"


import argparse
import base64
import chardet
import configparser
import humanize
import io
import json
import logging
import os
import sys
import xxhash
import zipfile

from datetime import datetime


_name_ = "wabbajack_cleaner"


_ARCH_EXTS = [".7z", ".rar", ".zip"]
_ARGS = None
_DOWNLOADS = None
_LOGGER = None
_MODLIST = None
_MODLIST_JSON = "modlist.json"


def hash_file(path):
    if not os.path.isfile(path):
        _LOGGER.error(f"Path does not exist: {path}.")
        sys.exit(1)

    xxh64 = xxhash.xxh64()

    with open(path, "rb") as file:
        buff = file.read(io.DEFAULT_BUFFER_SIZE)
        while len(buff) > 0:
            xxh64.update(buff)
            buff = file.read(io.DEFAULT_BUFFER_SIZE)

    digest = xxh64.digest()
    digest_le = bytearray(reversed(digest))
    b64 = base64.b64encode(digest_le)
    b64_string = b64.decode()
    return b64_string


def init_logging():
    global _LOGGER

    _LOGGER = logging.getLogger(_name_)
    _LOGGER.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(f"{_name_}_{datetime.now():%Y%m%d}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    _LOGGER.addHandler(file_handler)
    _LOGGER.addHandler(stdout_handler)


def init_args():
    global _ARGS

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        help="Print the version number and exit.",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--modlist-path", help="Specifies the path to a Wabbajack modlist file."
    )

    parser.add_argument(
        "--downloads-dir",
        help="Specifies the Wabbajack directory with downloaded mods.",
    )

    parser.add_argument(
        "--dry-run",
        help="Perform analysis without actually deleting files.",
        action="store_true",
        default=False,
    )

    _ARGS = parser.parse_args()


def check_args():
    if not _ARGS:
        _LOGGER.error("No arguments were found.")
        sys.exit(1)

    if not _ARGS.modlist_path:
        _LOGGER.error("Modlist path argument was not found: --modlist-path.")
        sys.exit(1)

    if not os.path.exists(_ARGS.modlist_path):
        _LOGGER.error(f"Path does not exist: {_ARGS.modlist_path}.")
        sys.exit(1)

    if not _ARGS.downloads_dir:
        _LOGGER.error("Modlist path argument was not found: --downloads-dir.")
        sys.exit(1)

    if not os.path.exists(_ARGS.downloads_dir):
        _LOGGER.error(f"Path does not exist: {_ARGS.downloads_dir}.")
        sys.exit(1)


def extract_modlist_json():
    global _MODLIST

    _LOGGER.info(f"Extracting modlist.json from file: {_ARGS.modlist_path}.")

    with zipfile.ZipFile(_ARGS.modlist_path) as zip:
        with open(_MODLIST_JSON, "wb") as file:
            file.write(zip.read("modlist"))

    _LOGGER.info(f"Validating JSON file: {_MODLIST_JSON}.")

    try:
        with open(_MODLIST_JSON, "r") as file:
            modlist = json.load(file)
    except json.JSONDecodeError:
        _LOGGER.error(f"Failed to read JSON file: {_MODLIST_JSON}.")
        sys.exit(1)

    _LOGGER.info(f"Pretty printing JSON in file: {_MODLIST_JSON}.")

    with open(_MODLIST_JSON, "w") as file:
        json.dump(modlist, file, indent=4)

    _LOGGER.info(f"Analyzing modlist format in file: {_MODLIST_JSON}.")

    if "Archives" not in modlist:
        _LOGGER.error(
            f'Modlist format error: tag "Archives" was not found in file: {_MODLIST_JSON}.'
        )
        sys.exit(1)

    _MODLIST = {}

    for archive in modlist["Archives"]:
        if "Name" not in archive:
            _LOGGER.error(
                f'Modlist format error: tag "Name" was not found in file: {_MODLIST_JSON}; {str(archive)}.'
            )
            sys.exit(1)

        if "Hash" not in archive:
            _LOGGER.error(
                f'Modlist format error: tag "Hash" was not found in file: {_MODLIST_JSON}; {str(archive)}.'
            )
            sys.exit(1)

        if archive["Name"] in _MODLIST:
            _LOGGER.error(
                f"Duplicate entry found in file: {_MODLIST_JSON}; {str(archive)}."
            )
            sys.exit(1)

        _MODLIST[archive["Name"]] = archive

    modlist_len = len(_MODLIST)
    _LOGGER.info(f"Found {modlist_len} mods in modlist file: {_ARGS.modlist_path}.")


def get_downloaded_mods():
    global _DOWNLOADS

    _LOGGER.info(f"Searching for mod archives in directory: {_ARGS.downloads_dir}.")

    _DOWNLOADS = {}
    for root, _, files in os.walk(_ARGS.downloads_dir):
        for name in files:
            _, extension = os.path.splitext(name)
            if extension not in _ARCH_EXTS:
                continue
            file_path = os.path.join(root, name)
            _DOWNLOADS[name] = {
                "extension": extension,
                "path": file_path,
                "size": os.stat(file_path).st_size,
                "keep": True,
                "hash": None,
            }

    total_archs = len(_DOWNLOADS)

    if total_archs == 0:
        _LOGGER.error(f"No archives were found in directory: {_ARGS.downloads_dir}.")
        sys.exit(1)

    _LOGGER.info(f"Found {total_archs} archives in directory: {_ARGS.downloads_dir}.")


def analyze_installed_mods():
    _LOGGER.info(f"Analyzing mod list: {_ARGS.modlist_path}.")

    without_archive = []
    for name in _MODLIST.keys():
        if name not in _DOWNLOADS:
            archive = _MODLIST[name]

            if "State" in archive:
                if "GameFileSourceDownloader" in str(archive["State"]):
                    continue

            without_archive.append(name)

            _LOGGER.info(f"Mod without archive: {archive['Name']}.")

    found_archive = {}
    if len(without_archive) > 0:
        _LOGGER.info(f"Searching for {len(without_archive)} mod archives using hash.")
        inx = 0
        while True:
            if len(without_archive) == 0:
                break
            if inx >= len(without_archive):
                break
            name = without_archive[inx]
            file_hash = _MODLIST[name]["Hash"]
            _LOGGER.info(f"Searching for mod archive with hash: {file_hash}.")
            is_found = False
            for file in _DOWNLOADS:
                download = _DOWNLOADS[file]
                if not download["hash"]:
                    download["hash"] = hash_file(download["path"])
                if file_hash == download["hash"]:
                    _LOGGER.info(
                        f'Found mod archive: "{download["path"]}" ({download["hash"]}).'
                    )
                    found_archive[file] = download["path"]
                    without_archive.pop(inx)
                    is_found = True
                    break
            if is_found:
                continue
            else:
                _LOGGER.info(f"Unable to find mod archive: {name}.")
            inx += 1

    _LOGGER.info(f"Analyzing downloads directory: {_ARGS.downloads_dir}.")

    not_installed = []
    ni_size = 0
    for file in _DOWNLOADS.keys():
        if file not in _MODLIST:
            if file in found_archive:
                continue

            not_installed.append(file)
            ni_size += _DOWNLOADS[file]["size"]

            _DOWNLOADS[file]["keep"] = False

            meta_fn = os.path.join(_ARGS.downloads_dir, f"{file}.meta")

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
                    f"Mod is not on the modlist (metadata: installed={_DOWNLOADS[file]['installed']}; removed={_DOWNLOADS[file]['removed']}): {file} ({humanize.naturalsize(_DOWNLOADS[file]['size'])})."
                )
            else:
                _LOGGER.info(f"Not installed mod: {file}.")

    _LOGGER.info(f"Mods without archive: {len(without_archive)}.")
    _LOGGER.info(
        f"Not installed mods: {len(not_installed)} ({humanize.naturalsize(ni_size)})."
    )


def clean_downloads():
    _LOGGER.info(
        f"Cleaning downloads directory (--dry-run={_ARGS.dry_run}): {_ARGS.downloads_dir}."
    )

    removed_cnt = 0
    removed_size = 0
    for file in _DOWNLOADS.keys():
        if _DOWNLOADS[file]["keep"]:
            continue
        file_path = os.path.join(_ARGS.downloads_dir, file)
        if _ARGS.dry_run:
            _LOGGER.info(
                f"(Not really) Deleting archive: {file_path} ({humanize.naturalsize(_DOWNLOADS[file]['size'])})."
            )
        else:
            _LOGGER.info(
                f"Deleting archive: {file_path} ({humanize.naturalsize(_DOWNLOADS[file]['size'])})."
            )
            os.remove(file_path)
        removed_cnt += 1
        removed_size += _DOWNLOADS[file]["size"]

    _LOGGER.info(
        f"Removed {removed_cnt} archive files in directory (--dry-run={_ARGS.dry_run}): {_ARGS.downloads_dir} ({humanize.naturalsize(removed_size)})."
    )


def main():
    init_args()

    if _ARGS.version:
        print(__version__)
        sys.exit(0)

    init_logging()
    check_args()

    t_0 = datetime.now()
    _LOGGER.info(f"{_name_} {__version__} started.")

    extract_modlist_json()
    get_downloaded_mods()
    analyze_installed_mods()
    clean_downloads()

    t_1 = datetime.now()
    total_seconds = (t_1 - t_0).total_seconds()

    _LOGGER.info(f"{_name_} {__version__} finished in {total_seconds:.2f} seconds.")


if __name__ == "__main__":
    main()
