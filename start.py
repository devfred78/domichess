# -*- coding: utf-8 -*-

"""
DomiChess, a simple chess game for Windows, written in Python.
Copyright (C) 2023 [devfred78](https://github.com/devfred78)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
	Main entry point to Domichess
"""

# Standard modules
# -----------------
import contextlib
import filecmp
import itertools
import logging
import os
from pathlib import Path
import shutil
import sys
import tomllib

# Third party modules
# --------------------
from colorlog import ColoredFormatter

# Predefinite functions
# ----------------------
def is_64bit():
    """
    Tests if the current Python interpreter is the 64-bit declination.

    Parameters
    ----------
    None

    Returns
    -------
    True if the current Python interpreter is 64-bit, False otherwise (typically for a 32-bit declination)
    """
    return sys.maxsize > 2**32


def copy_correct_cairodll():
    """
    Copy the correct `cairo.dll` file regarding the Python interpreter is a 32-bit or 64-bit platform.

    Parameters
    ----------
    None

    Returns
    -------
    '64bit' if the 64-bit version of the dll has been copied, '32bit' if the 32-bit version of the dll has been copied, or None if no file has been copied.
    """
    cairo32bitdll_path = Path(__file__).resolve().parent / Path("cairo_32bit.dll")
    cairo64bitdll_path = Path(__file__).resolve().parent / Path("cairo_64bit.dll")
    current_cairodll_path = Path(__file__).resolve().parent / Path("cairo.dll")
    if not current_cairodll_path.exists():
        # Check the current Python plateform (32 or 64 bit) and copy the suitable dll
        if is_64bit():
            shutil.copy2(cairo64bitdll_path, current_cairodll_path)
            return "64bit"
        else:
            shutil.copy2(cairo32bitdll_path, current_cairodll_path)
            return "32bit"
    else:
        # Check if the current cairo.dll file is the same as the one suitable with the current Python Platform (32 or 64 bit) and replace it if necessary
        if is_64bit():
            if not filecmp.cmp(str(current_cairodll_path), str(cairo64bitdll_path)):
                shutil.copy2(cairo64bitdll_path, current_cairodll_path)
                return "64bit"
        else:
            if not filecmp.cmp(str(current_cairodll_path), str(cairo32bitdll_path)):
                shutil.copy2(cairo32bitdll_path, current_cairodll_path)
                return "32bit"


# Internal modules
# -----------------
dll_copied = copy_correct_cairodll()
import domichess
from domichess import ENGINE_PATH

# Global constants
# -----------------

# namedtuples
# ------------

# Dataclasses
# ------------

# Classes
# --------


# Functions
# ----------
def get_version():
    """
    Get the current version of DomiChess from the pyproject.toml file. It assumes the use of Poetry.

    Parameters
    ----------
    None

    Returns
    -------
    A string with the current version, or None if the version information is not available.
    """
    pyproject_path = Path(__file__).resolve().parent / Path("pyproject.toml")
    if pyproject_path.is_file():
        try:
            with pyproject_path.open("rb") as pyproject_file:
                pyproject_toml = tomllib.load(pyproject_file)
            return pyproject_toml["tool"]["poetry"]["version"]
        except tomllib.TOMLDecodeError:
            return
    else:
        return


# Main function
# --------------
def main():
    """Main program execution"""

    global dll_copied
    # logging initialization
    logger = logging.getLogger("main")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    formatter = ColoredFormatter(
        "%(log_color)s[%(asctime)s][%(levelname)s][%(name)s]:%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )
    handler.setFormatter(formatter)

    # Debug mode setting
    if len(sys.argv) >= 2:
        if "--err" in sys.argv:
            display_err = True
        else:
            display_err = False
        if "--debug" in sys.argv[1].lower():
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)
        elif "--info" in sys.argv[1].lower():
            handler.setLevel(logging.INFO)
            logger.addHandler(handler)
        else:
            logger.addHandler(logging.NullHandler())
    else:
        display_err = False
        logger.addHandler(logging.NullHandler())

    # `engines` directory creation (if not already existing) in all cases
    if getattr(sys, "frozen", False):
        app_path = Path(sys.executable).parent
    else:
        app_path = Path(__file__).resolve().parent
    engine_path = app_path / Path(ENGINE_PATH)
    if not engine_path.is_dir():
        indicator_file = engine_path / Path("PLACE_CHESS_ENGINES_HERE")
        if not engine_path.exists():
            engine_path.mkdir()
            indicator_file.touch()
        else:
            for i in itertools.count():
                engine_path = engine_path.with_stem(engine_path.stem + str(i))
                if not engine_path.exists():
                    engine_path.mkdir()
                    indicator_file.touch()
                    break

    # Display execution
    logger.info("**************************************")
    logger.info("**")
    logger.info(f"**   DomiChess version {get_version()}")
    logger.info("**")
    logger.info("**************************************")
    if dll_copied == "32bit":
        logger.warning("The 32-bit version of cairo.dll has been found and installed.")
    elif dll_copied == "64bit":
        logger.warning("The 64-bit version of cairo.dll has been found and installed.")
    elif is_64bit():
        logger.info("The 64-bit version of cairo.dll is already installed.")
    else:
        logger.info("The 32-bit version of cairo.dll is already installed.")
    if display_err:
        display = domichess.display.Display(
            version=get_version(), engine_path=engine_path, logger=logger
        )
        display.start_display()
    else:
        with contextlib.redirect_stderr(open(os.devnull, "w")):
            display = domichess.display.Display(
                version=get_version(), engine_path=engine_path, logger=logger
            )
            display.start_display()

    # The end !
    logger.info("**************************************")
    logger.info("**")
    logger.info("** DomiChess is finished for now.")
    logger.info("** See you soon !")
    logger.info("**")
    logger.info("**************************************")


# Main program,
# running only if the module is NOT imported (but directly executed)
# -------------------------------------------------------------------
if __name__ == "__main__":
    main()
