# Filename: wabbajack_cleaner.py
# Author: Tim Makarov
# Created: 2025-02-01
# Description: Wabbajack Cleaner is a tool for cleaning downloaded mods directory.


__author__ = "Tim Makarov"
__copyright__ = "Copyright 2025, Tim Makarov"
__credits__ = ["github.com/timothy-makarov"]
__email__ = "timothy.makarov@gmail.com"
__license__ = "GPL"
__maintainer__ = "Tim Makarov"
__status__ = "Prototype"
__version__ = "0.3.0"


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


class ModArchive:
    def __parse_meta(self):
        meta_enc = None

        try:
            with open(self.meta_path, "rb") as file:
                meta_enc = chardet.detect(file.read())["encoding"]
        except Exception:
            logging.error(
                f'Failed to detect encoding of mod meta file "{self.meta_path}".'
            )
            sys.exit(1)

        meta = configparser.ConfigParser()

        try:
            meta.read(self.meta_path, encoding=meta_enc)
        except Exception:
            logging.error(f'Failed to parse mod meta file "{self.meta_path}".')
            sys.exit(1)

        if "General" not in meta:
            logging.error(
                f'Bad format of mod meta file "{self.meta_path}": missing "General" section.'
            )
            sys.exit(1)

        general = meta["General"]

        if "installed" in general:
            self.m_installed = general["installed"] == "true"
        else:
            self.m_installed = None

        if "removed" in general:
            self.m_removed = general["removed"] == "true"
        else:
            self.m_removed = None

    def __xxh64_file(self):
        xxh64 = xxhash.xxh64()

        with open(self.path, "rb") as file:
            buff = file.read(io.DEFAULT_BUFFER_SIZE)
            while len(buff) > 0:
                xxh64.update(buff)
                buff = file.read(io.DEFAULT_BUFFER_SIZE)

        digest = xxh64.digest()
        digest_le = bytearray(reversed(digest))
        b64 = base64.b64encode(digest_le)
        self.hash = b64.decode()

    def __init__(self, path):
        if path is None or len(path) == 0:
            logging.error("Mod file path cannot be null or empty.")
            sys.exit(1)

        if not os.path.isfile(path):
            logging.error(f'Mod file "{path}" was not found.')
            sys.exit(1)

        self.hash = None

        self.path = path
        self.file_size = os.stat(self.path).st_size

        f_path, f_name = os.path.split(path)
        self.name = f_name
        _, f_ext = os.path.splitext(f_name)

        if f_ext not in [".7z", ".rar", ".zip"]:
            logging.error(f'Unknown mod file extension "{path}".')
            sys.exit(1)

        self.meta_path = os.path.join(f_path, f"{f_name}.meta")

        if not os.path.isfile(self.meta_path):
            logging.error(f'Mod meta file "{self.meta_path}" was not found.')
            sys.exit(1)

        self.__parse_meta()

    def get_name(self):
        return self.name

    def get_size(self):
        return self.file_size

    def get_hash(self):
        if self.hash is None:
            self.__xxh64_file()

        return self.hash

    def remove(self, force_delete=False):
        if self.m_installed is not None:
            if self.m_installed:
                if force_delete:
                    logging.info(f"Removing mod archive (force): {self.path}.")
                    os.remove(self.path)
                    logging.info(f"Removing mod meta file (force): {self.meta_path}.")
                    os.remove(self.meta_path)
                    return
                else:
                    logging.critical(f'Cannot delete installed mod "{self.path}".')
                    return

        if self.m_removed is not None:
            if self.m_removed:
                logging.info(f"Removing mod archive: {self.path}.")
                os.remove(self.path)
                logging.info(f"Removing mod meta file: {self.meta_path}.")
                os.remove(self.meta_path)
                return


class Downloads:
    def __init__(self, directory):
        if directory is None or len(directory) == 0:
            logging.error("Modlist download directory cannot be null or empty.")
            sys.exit(1)

        if not os.path.isdir(directory):
            logging.error(f'Modlist download directory "{directory}" was not found.')
            sys.exit(1)

        self.directory = directory
        self.archives = {}

        logging.info(f'Scanning directory "{self.directory}".')
        files = os.listdir(self.directory)
        for file in files:
            _, f_ext = os.path.splitext(file)
            if f_ext not in [".7z", ".rar", ".zip"]:
                continue
            file = os.path.join(self.directory, file)
            if file in self.archives:
                logging.error(f"Duplicate mod file entry was found: {file}.")
                sys.exit(1)
            else:
                self.archives[file] = ModArchive(file)
        logging.info(f"Found {len(self.archives)} mod archives.")

    def iter_mods(self):
        for file in self.archives:
            yield self.archives[file]


class Modlist:
    def __unzip_modlist(self):
        with zipfile.ZipFile(self.zip_path) as zip:
            with open(self.json_path, "wb") as file:
                file.write(zip.read("modlist"))

    def __validate_size(self):
        file_size = os.stat(self.zip_path).st_size
        meta_size = int(self.meta["download_metadata"]["Size"])
        if file_size != meta_size:
            logging.error(
                f'Modlist "{self.zip_path}" file size does not equal to its size from "{self.meta_path}".'
            )
            sys.exit(1)

    def __iter_archives(self):
        if "Archives" not in self.modlist:
            return None

        archives = self.modlist["Archives"]

        for archive in archives:
            if "State" not in archive:
                continue
            state = archive["State"]
            if "$type" not in state:
                continue
            _type = state["$type"]
            if "NexusDownloader" not in _type or "Wabbajack.Lib" not in _type:
                continue
            yield archive

    def __parse_modlist(self):
        self.game_type = self.modlist["GameType"]
        logging.info(f"Game type: {self.game_type}.")

        self.version = self.modlist["Version"]
        logging.info(f"Modlist version: {self.version}.")

        self.modlist_by_file = {}
        self.modlist_by_hash = {}
        for mod in self.__iter_archives():
            if "Name" not in mod:
                logging.error(f'Mod JSON contains no "Name" attribute: {str(mod)}.')
                sys.exit(1)

            name = mod["Name"]

            if name in self.modlist_by_file:
                logging.error(f'Duplicate "Name" entry found in modlist JSON: {name}.')
                sys.exit(1)

            self.modlist_by_file[name] = mod

            if "Hash" not in mod:
                logging.error(f'Mod JSON contains no "Hash" attribute: {str(mod)}.')
                sys.exit(1)

            _hash = mod["Hash"]

            if _hash in self.modlist_by_hash:
                logging.error(f'Duplicate "Hash" entry found in modlist JSON: {_hash}.')
                sys.exit(1)

            self.modlist_by_hash[_hash] = mod

        del self.modlist["Archives"]

    def __init__(self, zip_path):
        if zip_path is None or len(zip_path) == 0:
            logging.error("Modlist file path cannot be null or empty.")
            sys.exit(1)

        if not os.path.isfile(zip_path):
            logging.error(f'Modlist file "{zip_path}" was not found.')
            sys.exit(1)

        f_path, f_name = os.path.split(zip_path)
        f_name, f_ext = os.path.splitext(f_name)

        if f_ext != ".wabbajack":
            logging.error(
                f'Modlist file extension must be ".wabbajack", but got "{f_ext}".'
            )
            sys.exit(1)

        self.zip_path = zip_path

        self.uid = int(f"{datetime.now():%Y%m%d%H%M%S}")
        logging.info(f"Current modlist processing UID {self.uid}.")

        self.json_path = os.path.join(os.getcwd(), f"{self.uid}-modlist.json")

        if os.path.isfile(self.json_path):
            logging.error(f'Modlist JSON file "{self.json_path}" already exists.')
            sys.exit(1)

        self.meta_path = os.path.join(f_path, f"{f_name}.wabbajack.metadata")

        if not os.path.isfile(self.meta_path):
            logging.error(f'Modlist metadata file "{self.meta_path}" was not found.')
            sys.exit(1)

        logging.info(f'Parsing modlist metadata JSON "{self.meta_path}".')
        try:
            with open(self.meta_path, "r") as file:
                self.meta = json.load(file)
        except json.JSONDecodeError:
            logging.error(f'Failed to load modlist metadata JSON "{self.meta_path}".')
            sys.exit(1)

        self.meta_path = os.path.join(os.getcwd(), f"{self.uid}-modlist.metadata.json")

        if os.path.isfile(self.meta_path):
            logging.error(
                f'Modlist metadata JSON file "{self.meta_path}" already exists.'
            )
            sys.exit(1)

        logging.info(f'Pretty printing modlist metadata JSON file "{self.meta_path}".')
        with open(self.meta_path, "w") as file:
            json.dump(self.meta, file, indent=4)

        self.archives_count = int(self.meta["download_metadata"]["NumberOfArchives"])
        if self.archives_count <= 0:
            logging.error(f"Metadata file reports {self.archives_count} mod archives.")
            sys.exit(1)

        logging.info("Validating modlist metadata.")
        self.__validate_size()

        zip_size = os.stat(self.zip_path).st_size
        logging.info(
            f"Unpacking modlist JSON ({humanize.naturalsize(zip_size)} zipped)."
        )
        self.__unzip_modlist()

        logging.info(f'Parsing modlist JSON "{self.json_path}".')
        try:
            with open(self.json_path, "r") as file:
                self.modlist = json.load(file)
        except json.JSONDecodeError:
            logging.error(f'Failed to load modlist JSON "{self.json_path}".')
            sys.exit(1)

        logging.info(f'Pretty printing modlist JSON file "{self.json_path}".')
        with open(self.json_path, "w") as file:
            json.dump(self.modlist, file, indent=4)

        self.modlist_by_file = None
        self.modlist_by_hash = None
        self.__parse_modlist()

    def get_mod_by_file(self, file):
        if file in self.modlist_by_file:
            return self.modlist_by_file[file]
        return None

    def get_mod_by_hash(self, file_hash):
        if file_hash in self.modlist_by_hash:
            return self.modlist_by_hash[file_hash]
        return None

    def remove_temp_files(self):
        if os.path.isfile(self.json_path):
            os.remove(self.json_path)

        if os.path.isfile(self.meta_path):
            os.remove(self.meta_path)


def init_logging():
    format = "%(asctime)s [%(levelname)s]: %(message)s"

    logging.basicConfig(
        format=format,
        filename=f"{_name_}_{datetime.now():%Y%m%d}.log",
        level=logging.DEBUG,
    )

    formatter = logging.Formatter(format)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(stdout_handler)


def init_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        help="Print the program version and exit.",
        action="store_true",
        default=False,
    )

    parser.add_argument("--modlist-file", help="Wabbajack modlist file.")

    parser.add_argument(
        "--download-dir",
        help="Wabbajack mod download directory.",
    )

    parser.add_argument(
        "--dry-run",
        help="Run the program, but do not delete actual files.",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--force-delete",
        help="Ignore modlist errors and delete archive files anyway.",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    if args.modlist_file is None:
        logging.error("No modlist was specified: --modlist-file.")
        sys.exit(1)

    if not os.path.exists(args.modlist_file):
        logging.error(f"File was not found: {args.modlist_file}.")
        sys.exit(1)

    if args.download_dir is None:
        logging.error("No mod download directory was specified: --download-dir.")
        sys.exit(1)

    if not os.path.exists(args.download_dir):
        logging.error(f"Path does not exist: {args.download_dir}.")
        sys.exit(1)

    return args


def main():
    args = init_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    init_logging()

    t_0 = datetime.now()
    logging.info(f"{_name_} {__version__} started.")

    modlist = Modlist(args.modlist_file)
    downloads = Downloads(args.download_dir)

    found = []
    found_size = 0
    for arch in downloads.iter_mods():
        file = arch.get_name()
        mod = modlist.get_mod_by_file(file)
        if mod is not None:
            continue
        mod = modlist.get_mod_by_hash(arch.get_hash())
        if mod is not None:
            continue
        found.append(arch)
        found_size += arch.get_size()
        logging.warning(
            f'Archive "{file}" (Size: {humanize.naturalsize(arch.get_size())}, Hash: {arch.get_hash()}) was not found in the modlist.'
        )

    if len(found) > 0:
        logging.info(
            f"Found {len(found)} archives not in the modlist in total {humanize.naturalsize(found_size)}."
        )

        for arch in found:
            if args.dry_run:
                logging.info(
                    f"Removing (not really): {arch.get_name()} ({humanize.naturalsize(arch.get_size())})."
                )
            else:
                arch.remove(force_delete=args.force_delete)
    else:
        logging.info("All is clean. Nothing to do.")

    modlist.remove_temp_files()

    t_1 = datetime.now()
    total_seconds = (t_1 - t_0).total_seconds()

    logging.info(f"{_name_} {__version__} finished in {total_seconds:.2f} seconds.")


if __name__ == "__main__":
    main()
