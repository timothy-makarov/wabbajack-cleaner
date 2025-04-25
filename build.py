# Filename: build.py
# Author: Tim Makarov
# Created: 2025-02-01
# Description: This is a build script for Wabbajack Cleaner.


import wabbajack_cleaner
import PyInstaller.__main__


__author__ = wabbajack_cleaner.__author__
__copyright__ = wabbajack_cleaner.__copyright__
__credits__ = wabbajack_cleaner.__credits__
__email__ = wabbajack_cleaner.__email__
__license__ = wabbajack_cleaner.__license__
__maintainer__ = wabbajack_cleaner.__maintainer__
__status__ = wabbajack_cleaner.__status__
__version__ = wabbajack_cleaner.__version__


if __name__ == "__main__":
    PyInstaller.__main__.run(
        [
            f"{wabbajack_cleaner._name_}.py",
            "--clean",
            "--noconfirm",
            "--onefile",
        ]
    )
