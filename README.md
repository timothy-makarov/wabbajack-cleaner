# Wabbajack Cleaner

**Wabbajack Cleaner** is an automated Modlist Cleaner that can remove [Wabbajack](https://www.wabbajack.org/) old archives from the downloads directory.

## How It Works

**Wabbajack Cleaner** analyzes the Wabbajack [modlist](https://wiki.wabbajack.org/modlist_author_documentation/Introduction.html) file and searches the directory with downloaded mods for archives that are not on the mod list.

## How To

Run help for arguments description:

```
python .\wabbajack_cleaner.py --help
```

### WARNING!

Always run with `--dry-run` argument first.

### Analyze Modlist and Downloads Directory

```
python .\wabbajack_cleaner.py --modlist-file "D:\SteamLibrary\Wabbajack\4.0.1.0\downloaded_mod_lists\LoreRim_@@_LoreRim.wabbajack" --download-dir "D:\LoreRim\downloads" --dry-run
```

Make sure you won't delete anything useful.

**Wabbajack Cleaner** produces log file which can be helpful.

### Run the Cleanup

```
python .\wabbajack_cleaner.py --modlist-file "D:\SteamLibrary\Wabbajack\4.0.1.0\downloaded_mod_lists\LoreRim_@@_LoreRim.wabbajack" --download-dir "D:\LoreRim\downloads"
```

#### Ignore Modlist Errors

```
python .\wabbajack_cleaner.py --modlist-file "D:\SteamLibrary\Wabbajack\4.0.1.0\downloaded_mod_lists\LoreRim_@@_LoreRim.wabbajack" --download-dir "D:\LoreRim\downloads" --force-delete
```

### Windows Executable

**Wabbajack Cleaner** releases also contain a prebuild Windows executable binary `wabbajack_cleaner.exe`.

Usage is similar:

```
.\wabbajack_cleaner.exe --modlist-file "D:\SteamLibrary\Wabbajack\4.0.1.0\downloaded_mod_lists\LoreRim_@@_LoreRim.wabbajack" --download-dir "D:\LoreRim\downloads" --dry-run
```

EXE file is created with `build.py` script using [PyInstaller](https://pyinstaller.org/).
