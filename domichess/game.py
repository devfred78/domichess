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
	Module game: game management
"""


# Standard modules
# -----------------
from collections import UserDict
import logging
from uuid import uuid4

# Third party modules
# --------------------
import chess
import chess.engine
import PySimpleGUI as sg

# Internal modules
# -----------------
from domichess import Result
from domichess import Type, EngineProtocol
from domichess import HELP_DURATION

# namedtuples
# ------------


# Global constants
# -----------------


# Dataclasses
# ------------

# Classes
# --------


class Player:
    """
    This class represents a player.

    Attributes
    ----------
    name: str
            Name of the player
    uuid: str
            Universal unique identifier
    color: chess.Color
            Color of the player (black or white)
    type: domichess.Type
            Type of player (human, cpu or remote)


    Methods
    -------


    """

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      INITIALIZATION
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    def __init__(
        self, name="Player", color=chess.WHITE, type=Type.HUMAN, uuid=None, logger=None
    ):
        """
        Player instance initialization.

        Parameters
        ----------
        name: str, optional
                Name of the player (default: "Player")
        color: chess.Color, optional
                Color of the player (default: chess.WHITE)
        type: domichess.Type, optional
                Type of player (default: Type.HUMAN)
        uuid: str, optional
                universal unique identifier. if None (the default), a new value is created during initialization. Cannot be changed once the object is instanciated.
        logger : logging.Logger object, optional
                The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.
        """

        if logger is None:
            self.log = logging.getLogger("Player")
            self.log.addHandler(logging.NullHandler())
        else:
            self.log = logger.getChild("Player")

        self.log.debug("--- Player initialization ---")

        # Internal attributes initialization
        self._name = name  # Name of the player
        self._color = color  # Color of the player (white or black)
        self._type = type  # Type of the player (human, cpu or network)
        if uuid is None:  # identifier of the player
            self._uuid = str(uuid4())
        else:
            self._uuid = uuid

        self.log.debug(
            f"--- {'White' if self._color else 'Black'} player initialization ---"
        )

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      ATTRIBUTES
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    #####################################
    # Public attributes

    @property
    def name(self):
        """
        String representing the name of the player.
        """
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise ValueError("name must be a string.")
        else:
            self.log.debug(
                f"The name of the {'white' if self.color else 'black'} player has been changed into {value}."
            )
            self._name = value

    @property
    def color(self):
        """
        Color of the player.

        This is a boolean value: True for the white player, False for the black one.
        """
        return self._color

    @color.setter
    def color(self, value):
        if not isinstance(value, bool):
            raise ValueError("color must be a boolean.")
        else:
            self.log.debug(
                f"{self.name} is now the {'white' if value else 'black'} opponent."
            )
            self._color = value

    @property
    def type(self):
        """
        Type of the player.

        3 possible values: Type.HUMAN for a local human, Type.CPU for the local CPU, Type.NETWORK for a remote opponent.
        """
        return self._type

    @type.setter
    def type(self, value):
        if value not in (Type.HUMAN, Type.CPU, Type.NETWORK):
            raise ValueError("Type must be Type.HUMAN, Type.CPU or Type.NETWORK.")
        else:
            if value == Type.HUMAN:
                self.log.debug(
                    f"The {'white' if self.color else 'black'} player {self.name} is now a local human."
                )
            elif value == Type.CPU:
                self.log.debug(
                    f"The {'white' if self.color else 'black'} player {self.name} is now the local CPU."
                )
            else:
                self.log.debug(
                    f"The {'white' if self.color else 'black'} player {self.name} is now a remote opponent."
                )
            self._type = value

    @property
    def uuid(self):
        """
        Unique identifier of the player.

        This is a read-only, string attribute.
        """
        return self._uuid


class PlayerDict(UserDict):
    """
    Dictionnary used to store the players in a Game instance.

    Create or update a value only if the key is boolean (True - for white, or False - for Black) and the value is an instance of the Player class (or None). Otherwise it is silently rejected (no modification of the dictionary and no error raised).
    """

    def __setitem__(self, key, value):
        if isinstance(key, bool):
            if isinstance(value, Player) or (value is None):
                self.data[key] = value


class Game:
    """
    This class represents a game.

    Attributes
    ----------


    Methods
    -------


    """

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      INITIALIZATION
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    def __init__(
        self,
        name="game",
        white_player=None,
        black_player=None,
        helper_engine=None,
        uuid=None,
        logger=None,
    ):
        """
        Game instance initialization.

        Parameters
        ----------
        name: str, optional
                Name of the game. Default is "game"
        white_player: Player object, optional
                Object representing the white player. Default is None
        black_player: Player object, optional
                Object representing the black player. Default is None
        helper_engine: domichess.engine.Engine , optional
                Chess engine used to help. Default is none
        uuid: str, optional
                universal unique identifier. if None (the default), a new value is created during initialization. Can be modified until the game has started. After that, uuid is not modifiable.
        logger : logging.Logger object, optional
                The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.
        """
        if logger is None:
            self.log = logging.getLogger("Game")
            self.log.addHandler(logging.NullHandler())
        else:
            self.log = logger.getChild("Game")

        self.log.debug("--- Game initialization ---")

        # Internal attributes initialization
        self._name = name  # Name of the game
        self._ongoing = False  # flag signaling whether the game is ongoing or not
        if uuid is None:  # Identifier of the game
            self._uuid = str(uuid4())
        else:
            self._uuid = uuid
        self._board = chess.Board()  # board of the chess
        self._board.reset()
        # Helper initialization
        self._helper_engine = helper_engine

        # Players attribute initialization
        self.players = PlayerDict(
            {chess.WHITE: white_player, chess.BLACK: black_player}
        )

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
    def name(self):
        """
        String representing the name of the game.
        """
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise ValueError("name must be a string.")
        else:
            self.log.debug(f"The name of the game has been changed into {value}.")
            self._name = value

    @property
    def ongoing(self):
        """
        True if the game is ongoing, False if it is finished or not yet started.
        """
        return self._ongoing

    @ongoing.setter
    def ongoing(self, value):
        if not isinstance(value, bool):
            raise ValueError("ongoing must be a boolean.")
        else:
            if not value:  # close the helper engine if the game is over
                try:
                    self.helper_engine.quit()
                except:
                    pass
            self._ongoing = value

    @property
    def uuid(self):
        """
        Unique identifier of the game.

        Can be modified until the game has started. After that, uuid is not modifiable.
        """
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        if not self.ongoing:
            self._uuid = value

    @property
    def current_turn(self):
        """
        Rank of the current turn. Start at 1 and is incremented after every move of the black side.

        This attribute is read only.
        """
        return self._board.fullmove_number

    @property
    def current_color(self):
        """
        The side to move. True (chess.WHITE) for the white side, False (chess.BLACK) for the black side.

        This attribute is read only.
        """
        return self._board.turn

    @property
    def current_board(self):
        """
        A chess.BaseBoard object representing a copy of the current board.

        Warning: only the position of the pieces are copied, not the move stack.

        This attribute is read only.
        """
        return self._board.copy()

    @property
    def board(self):
        """
        A chess.board object representing the current board, including the move stack.

        This attribute is read only.
        """
        return self._board

    @property
    def result(self):
        """
        A chess.Outcome object bringing information about the outcome of the game (or None if the game is not yet ended).

        This attribute is read only.
        """
        return self._board.outcome()

    @property
    def result_with_claim(self):
        """
        A chess.Outcome object bringing information about the outcome of the game (or None if the game is not yet ended). it includes the cases of claimable draws (fifty-move rule or threefold repetition, checking the latter can be slow).

        Notice that if the result is a claimable draw, the game is not over until the draw is effectively claimed.

        This attribute is read only.
        """
        return self._board.outcome(claim_draw=True)

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

        # @staticmethod
        # def static_mehod(...):
        """
		Description
		
		Parameters
		----------
		
		Returns
		-------
		
		"""

    #####################################
    # Private methods

    def _send_move_uci_to_remote(self, uci_move):
        """
        Send the move to the remote player.

        Parameters
        ----------
        uci_move:	str, mandatory
                UCI representation of the move

        Returns
        -------

        """
        pass

    #####################################
    # Public methods

    def ask_for_help(self):
        """
        Ask the helper engine for finding the best next move, for the current position (and for the current player).

        This method blocks until the result is given.

        Parameters
        ----------
        None

        Returns
        -------
        A chess.Move object, representing the best move find by the helper engine.

        """
        if not self._helper_engine:
            return None
        else:
            if move := self._helper_engine.next_move(self._board):
                return move
            else:
                return None

    def add_move(self, move):
        """
        Add a move into the current game.

        Warning: The move is not checked for legality.

        Parameters
        ----------
        move:	chess.Move, mandatory
                move to add.

        Returns
        -------
        A namedtuple with 2 members:
                san: string representing the standard algebric notation (SAN) of the given move in the context of position before this move.
                over: True if the game is over, False otherwise
        """
        san = self._board.san(move)
        self._board.push(move)
        self.ongoing = not self._board.is_game_over()

        if self._board.is_game_over():
            if self.players[not self.current_color].type == Type.NETWORK:
                self._send_move_uci_to_remote(uci_move)
        else:
            if self.players[self.current_color].type == Type.NETWORK:
                self._send_move_uci_to_remote(uci_move)

        return Result(san=san, over=self._board.is_game_over())

    def reaching_squares_from_pos(self, start_pos):
        """
        Returns a tuple of chess.Square objects representing the reachable positions by the piece at the given square.

        Parameters
        ----------
        start_pos: chess.Sqaure, mandatory
                Position of the piece from where the reaching squares are calculated

        Returns
        -------
        The reachable squares in a tuple, possibly empty if no square is reachable.
        """
        reachable_squares = tuple(
            move.to_square
            for move in self._board.legal_moves
            if move.from_square == start_pos
        )

        return reachable_squares


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
