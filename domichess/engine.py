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
	Module engine: chess engine management
"""


# Standard modules
# -----------------
from collections import namedtuple
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, StrEnum, auto
import logging
import subprocess
import time
import threading
import typing

# Third party modules
# --------------------
import chess, chess.engine

# Internal modules
# -----------------
from domichess import EngineProtocol, UCIOptionType
from domichess import DEFAULT_SEARCH_TIME

# namedtuples
# ------------

# Enumerations
# -------------


# Global constants
# -----------------
UCI_TIMEOUT = (
    2.0  # Time out (in seconds) when asking either the engine is uci-compatible or not
)
OPTION_TIMEOUT = 1.0  # Time out (in seconds) when an option's update is attempted
COMMAND_TIMEOUT = 5.0  # Time out (in seconds) when a command to the engine is attempted

# Dataclasses
# ------------
@dataclass
class OptionItem:
    """
    Description of an engine's option.
    """

    name: str
    type: typing.Type[UCIOptionType] | None
    default: str | int | bool | float | None = None
    min: int | float | None = None
    max: int | float | None = None
    var: list[str | int | bool | float | None] = field(default_factory=list)
    value: str | int | bool | float | None = None

    def __call__(self):
        return self.value

    def __deepcopy__(self, memo):
        return OptionItem(
            name=deepcopy(self.name, memo),
            type=deepcopy(self.type, memo),
            default=deepcopy(self.default, memo),
            min=deepcopy(self.min, memo),
            max=deepcopy(self.max, memo),
            var=deepcopy(self.var, memo),
            value=deepcopy(self.value, memo),
        )

    def copy(self):
        """
        deepcopy emulation.

        !!! DO NOT USE THIS METHOD !!! Use copy.deepcopy() function instead.
        """
        return OptionItem(
            name=self.name,
            type=self.type,
            default=self.default,
            min=self.min,
            max=self.max,
            var=deepcopy(self.var),
            value=self.value,
        )


# Classes
# --------


class Options:
    """
    Engine'options. Empty by default, to be populated by an Engine's instance, during its initialization. All its attributes should be OptionItem dataclasse instances.
    """

    def __init__(self, chess_simple_engine=None, logger=None):
        """
        Options instance initialization.

        Parameters
        ----------
        chess_simple_engine: chess.engine.SimpleEngine object, optional
                Represents the engine to communicate with. If None (the default), the instance will be only used to store the options, without any communication with the engine.
        logger : logging.Logger object, optional
                The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.
        """
        if logger is None:
            self.log = logging.getLogger("Options")
            self.log.addHandler(logging.NullHandler())
        else:
            self.log = logger.getChild("Options")

        self.chess_simple_engine = chess_simple_engine

    def __dir__(self):
        """
        When dir() is applied on an instance of Options, it returns only the OptionItem objects added, hiding the special attributes (and methods) given by Python or personnalized here.
        """
        return [
            attr
            for attr in self.__dict__.keys()
            if not (
                attr.startswith("__")
                | (attr == "log")
                | (attr == "chess_simple_engine")
                | (attr == "copy")
                | (attr == "copy_without_engine")
            )
        ]

    # def __del__(self):
    # self.log.debug("Attempt to delete the option object")
    # self.chess_simple_engine.quit()
    # self.chess_simple_engine.close()
    # del self.chess_simple_engine

    def __setattr__(self, name, value):
        """
        Manages the assignment of an attribute.

        If the attempted value is an OptionItem object or an attribute of an OptionItem object already assigned, the value is successfully assigned as a new (or an updated) option.

        if the attempted value is another type, and the attribute already exists as an option (OptionItem object), the value is checked, and, depending on the type of option, the value is rejected or accepted. If accepted, the value is stored in the <option's name>.value attribute, and a communication is attempted to the engine in order to update the matching option.
        """
        if isinstance(value, OptionItem) | (name not in self.__dict__):
            object.__setattr__(self, name, value)
        else:
            option = object.__getattribute__(self, name)
            if isinstance(option, OptionItem):
                ok_for_update = False
                if option.type == UCIOptionType.CHECK:
                    if isinstance(value, bool):
                        ok_for_update = True
                        formatted_value = "true" if value else "false"
                    else:
                        raise ValueError(f"Expected {value} to be a boolean")
                elif option.type == UCIOptionType.SPIN:
                    if isinstance(value, int) | isinstance(value, float):
                        if (value >= option.min) and (value <= option.max):
                            ok_for_update = True
                            formatted_value = value
                        else:
                            raise ValueError(
                                f"Expected {value} to be between {option.min} and {option.max}"
                            )
                    else:
                        raise ValueError(
                            f"Expected {value} to be an integer or a float"
                        )
                elif option.type == UCIOptionType.COMBO:
                    if value in option.var:
                        ok_for_update = True
                        formatted_value = value
                    else:
                        raise ValueError(f"Expected {value} to be in {option.var}")
                elif option.type == UCIOptionType.BUTTON:
                    # Specific button case: the provided value is not relevant
                    if self.chess_simple_engine:
                        self.chess_simple_engine.configure({option.name: None})
                        self.log.debug(
                            f"Engine {self.chess_simple_engine.id['name']} updated: Button type option {option.name} switched"
                        )
                else:
                    ok_for_update = True
                    formatted_value = value
                if ok_for_update:
                    option.value = value
                    if self.chess_simple_engine:
                        if not self.chess_simple_engine.options[
                            option.name
                        ].is_managed():
                            self.chess_simple_engine.configure(
                                {option.name: formatted_value}
                            )
                            self.log.debug(
                                f"Engine {self.chess_simple_engine.id['name']} updated: Option {option.name} set to {formatted_value}"
                            )
            else:
                raise ValueError(
                    f"{name} is not an option for the engine {self.chess_simple_engine.id['name']}"
                )

    # def __getattribute__(self, name):
    # """
    # Manages the attribute accesses.

    # If the attribute to be accessed is an option (OptionItem object), the returned value is <option's name>.value.
    # In the other cases, the attribute is returned as-is, or an AttributeError is raised if the attribute is not implemented.
    # """
    # print(f"Try to access to the {name} option attribute")
    # if '.' in name:
    # option_name, attribute_name = name.split('.', maxsplit = 1)
    # return object.__attribute__(object.__attribute__(self, option_name), attribute_name)
    # else:
    # attr = object.__getattribute__(self, name)
    # if isinstance(attr, OptionItem):
    # return attr.value
    # else:
    # return attr

    def __deepcopy__(self, memo):
        options_copy = Options(self.chess_simple_engine, self.log)
        for option in dir(self):
            setattr(options_copy, option, deepcopy(getattr(self, option), memo))
        return options_copy

    def copy_without_engine(self, memo):
        """
        deepcopy of the instance, but without the engine. The copy will be only used to store the options, without any communication with the engine.
        """
        options_copy = Options(None, self.log)
        for option in dir(self):
            setattr(options_copy, option, deepcopy(getattr(self, option), memo))
        return options_copy


class Engine:
    """
    Represents a chess engine.

    LIMITATION : This class is only available for chess engines compliant with the UCI protocol. Other protocols (in particular: xboard) do not raise any exception, but set the protocol attribute to domichess.EngineProtocol.UNKNOWN, given the engine instance unusable. XBoard compatibility is planned for a further version, but not yet implemented.

    Attributes
    ----------
    log: logging.Logger object
            The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes.
    protocol: domichess.EngineProtocol object
            The protocol used to communicate with the chess engine. If domichess.EngineProtocol.UNKNOWN, the engine unusable.
    name: str
            Name of the chess engine, including the version number.
    author: str
            Author(s) of the chess engine.
    option: Options object, including one or more OptionItem object(s) as attribute
            Each OptionItem object represents one option provided by the chess engine. The name of the attribute is the name of the option, except that each (eventually successive) space(s) is (are) replaced by one '_'.
            Each option has the following attributes:
                    name: str = formal name of the option for the chess engine (with the eventual spaces)
                    type: UCIOptionType object = type of the option
                    default: the default value of the option, None if irrelevant
                    min: the minmium value of the option, None if irrelevant
                    max: the maximum value of the option, None if irrelevant
                    var: list of the predefined values of the option, None if irrelevant
                    value: the current value of the option, None if irrelevant
            In normal cases, the 'value' member should not to be invoked: to get the value, use the callable feature with the expression option.<option's name>(). To set the value, just use option.<option's name>. If set successfully, the engine is also automatically updated with the new value of this option.
    chess_simple_engine: chess.engine.SimpleEngine object
            Represents the engine to communicate with.
    engine_options: list
            List of the options provided by the engine. Each member (option) of this list can be reached by <Engine instance>.option.<option's name as provided in the list>.
    search_time: float
            Time, in seconds, to search for the next move
    game_name: str
            Name of the game the engine is currently playing. Expected to be different between two successive games.
    engine_is_closed: boolean
            Indicates if the wrapped engine is closed (True) or open (False). If the latter, then it is possible to add new moves or to update the options.
    Methods
    -------


    """

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      INITIALIZATION
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    def __init__(self, engine_path, logger=None, no_options=False):
        """
        Engine instance initialization.

        Parameters
        ----------
        engine_path: pathlib.Path object, mandatory
                Path to the chess engine
        logger : logging.Logger object, optional
                The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.
        no_options: boolean, optional
                If False (the default), the Engine instance populates its options, by asking the wrapped chess engine program. If True, no option is populated (usefull if you wish populate the options later).
        """

        if logger is None:
            self.log = logging.getLogger("Engine")
            self.log.addHandler(logging.NullHandler())
        else:
            self.log = logger.getChild("Engine")

        # Internal attributes initialization
        self.protocol = (
            EngineProtocol.UNKNOWN
        )  # Default value of self.protocol if an exception raises
        self._engine_path = engine_path
        self._no_options = no_options
        self.search_time = DEFAULT_SEARCH_TIME
        self.game_name = ""
        self.engine_is_closed = False
        if not self._is_uci_compatible():
            self.protocol = EngineProtocol.UNKNOWN

    def __del__(self):
        """
        Called when the instance is about to be destroyed. Quit the engine properly before.
        """
        self.log.debug(
            f"Attempt to unregister {self.name if self.protocol != EngineProtocol.UNKNOWN else self._engine_path.name} engine"
        )
        # del self.option
        self.quit()
        self.log.debug(
            f"{self.name if self.protocol != EngineProtocol.UNKNOWN else self._engine_path.name} engine successfully unregistred"
        )

    def __deepcopy__(self, memo):
        engine_copy = Engine(self._engine_path, self.log, no_options=True)
        engine_copy.option = deepcopy(self.option, memo)
        return engine_copy

    # ...

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      ATTRIBUTES
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    #####################################
    # Class attributes

    """ CLASS_ATTRIBUTE_1: type
			Class attribute description
	"""
    # CLASS_ATTRIBUTE_1 = xxx

    #####################################
    # Private attributes

    """ _private_attribute_1: type
			Private attribute description
	"""

    #####################################
    # Public attributes

    @property
    def engine_options(self):
        """
        List of the options provided by the engine.

        This is a read-only attribute.
        """
        return dir(self.option)

    # @property.setter
    # def public_attribute_2(self, value):
    # ...

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      METHODS
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    #####################################
    # Class methods

    # @classmethod
    # def class_method(cls, ...):

    #####################################
    # static methods

    @staticmethod
    def isfloat(number):
        """
        Tests if the number can be converted in a float.

        Inspired from https://www.programiz.com/python-programming/examples/check-string-number

        Parameters
        ----------
        number: str | int | float, mandatory
                The number to be tested

        Returns
        -------
        True if the number is the representation of a float (and can be converted into), False othewise.

        """
        try:
            float(number)
            return True
        except ValueError:
            return False

    #####################################
    # Private methods

    def _is_uci_compatible(self):
        """
        Tests if the given in self._engine_path is compatible with the UCI protocol. If compatible, populate the name, author, protocol, chess_simple_engine and option public attributes.

        Parameters
        ----------
        None

        Returns
        -------
        True if the engine is UCI-compatible, False otherwise.
        """
        try:
            self.chess_simple_engine = chess.engine.SimpleEngine.popen_uci(
                self._engine_path, timeout=COMMAND_TIMEOUT
            )
        except chess.engine.EngineError:
            self.log.warning(
                f"UCI Protocol error: {self._engine_path.name} seems not to be a compatible chess engine. Please consider deleting it from the engines directory."
            )
            return False
        else:
            self.protocol = EngineProtocol.UCI
            self.name = self.chess_simple_engine.id["name"]
            if "author" in self.chess_simple_engine.id:
                self.author = self.chess_simple_engine.id["author"]
            if not self._no_options:
                self.log.info(f"Compatible chess engine found: {self.name}")
                self.option = Options(self.chess_simple_engine, self.log)
                for option in self.chess_simple_engine.options.values():
                    if not option.is_managed():
                        formatted_name = "_".join(option.name.split())
                        setattr(
                            self.option,
                            formatted_name,
                            OptionItem(
                                name=option.name,
                                type=option.type,
                                default=option.default,
                                min=option.min,
                                max=option.max,
                                var=option.var if option.var else [],
                                value=option.default,
                            ),
                        )
                        self.log.debug(
                            f"{self.name} engine: option {option.name} added, with default value {option.default}"
                        )
            return True

    #####################################
    # Public methods

    def start_new_game(self, name="local"):
        """
        Start a new game.

        Parameters
        ----------
        name: str, optional
                Name of the game. Default is "local"

        Returns
        -------
        None

        """
        if name != self.game_name:
            self.game_name = name
        else:
            self.game_name = name + "_new"

    def next_move(self, board):
        """
        Asks the engine for the next move, in the context of the given board.

        Parameters
        ----------
        board: chess.Board object, mandatory
                The board (including moves from the starting position) to analyze

        Returns
        -------
        A chess.Move object representing the best move found by the engine.
        """
        return self.chess_simple_engine.play(
            board, chess.engine.Limit(time=self.search_time), game=self.game_name
        ).move

    def quit(self):
        """
        Closes the engine. This method is called when the object is deleted. If neccessary, it is possible to call this method directly, and, in this case, you can re-open the engine with the same personnalized options with the reopen() method.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        try:
            self.chess_simple_engine.quit()
            self.chess_simple_engine.close()
            self.engine_is_closed = True
        except (chess.engine.EngineTerminatedError, AttributeError):
            pass

    def reopen(self):
        """
        Opens again the chess engine, and apply the options previously set.

        Parameters
        ----------
        None

        Returns
        -------
        True if the re-open is a success, False otherwise.
        """
        if self.engine_is_closed:
            try:
                self.chess_simple_engine = chess.engine.SimpleEngine.popen_uci(
                    self._engine_path, timeout=COMMAND_TIMEOUT
                )
            except chess.engine.EngineError:
                self.log.warning(
                    f"UCI Protocol error: {self._engine_path.name} seems not to be a compatible chess engine. Please consider deleting it from the engines directory."
                )
                return False
            else:
                self.log.debug(
                    f"{self.name} engine is re-opened: the options are all set to their previously modified values."
                )
                memo = dict()
                recorded_options = deepcopy(self.option, memo)
                for option in self.engine_options:  # Apply the recorded option values
                    setattr(
                        self.option, option, getattr(recorded_options, option).value
                    )
        else:
            self.log.debug(
                f"{self._engine_path.name} seems to be already open. It is not necessary to re-open it."
            )
            return False


# Functions
# ----------


# Main function
# --------------
def main():
    """Main program execution"""
    print("Hello !")  # Example !!!


# Main program,
# running only if the module is NOT imported (but directly executed)
# -------------------------------------------------------------------
if __name__ == "__main__":
    main()
