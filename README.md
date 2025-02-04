# Wabbajack Cleaner

**Wabbajack Cleaner** is an automated Modlist Cleaner that can remove [Wabbajack](https://www.wabbajack.org/) old archives from the downloads directory.

## How It Works

**Wabbajack Cleaner** analyzes Wabbajack [modlist](https://wiki.wabbajack.org/modlist_author_documentation/Introduction.html) file and looks in the directory with downloaded mods for archives that are not on the modlist.

## How To

Run help for arguments description:

```
python .\wabbajack_cleaner.py --help
```

### WARNING!

Always run with `--dry-run` argument first.

### Analyze Modlist and Downloads Directory

```
python .\wabbajack_cleaner.py --modlist-path "D:\SteamLibrary\Wabbajack\3.7.5.3\downloaded_mod_lists\LoreRim_@@_LoreRim.wabbajack" --downloads-dir "D:\LoreRim\downloads" --dry-run
```

Make sure you won't delete anything useful.

**Wabbajack Cleaner** produces log file which can be helpful.

### Run the Cleanup

```
python .\wabbajack_cleaner.py --modlist-path "D:\SteamLibrary\Wabbajack\3.7.5.3\downloaded_mod_lists\LoreRim_@@_LoreRim.wabbajack" --downloads-dir "D:\LoreRim\downloads"
```

### Windows Executable

**Wabbajack Cleaner** releases also contain a prebuild Windows executable binary `wabbajack_cleaner.exe`.

Usage is similar:

```
.\wabbajack_cleaner.exe --modlist-path "D:\SteamLibrary\Wabbajack\3.7.5.3\downloaded_mod_lists\LoreRim_@@_LoreRim.wabbajack" --downloads-dir "D:\LoreRim\downloads" --dry-run
```

EXE file is created with `build.py` script using [PyInstaller](https://pyinstaller.org/).
