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

# Import standard modules
from enum import Enum, StrEnum, IntEnum, auto
from collections import namedtuple
import random

# Namedtuples
Result = namedtuple("Result", "san over")

# Enumerations
class Type(Enum):  # Possible types of player
    HUMAN = auto()
    CPU = auto()
    NETWORK = auto()


class Key(StrEnum):  # Keys for window elements
    CURRENT_GAME_TEXT = auto()
    CURRENT_GAME_NAME = auto()
    CURRENT_PLAYER_TEXT = auto()
    CURRENT_PLAYER_NAME = auto()
    CURRENT_PLAYER_IMAGE = auto()
    WHITE_LOGO = auto()
    BLACK_LOGO = auto()
    WHITE_NAME = auto()
    BLACK_NAME = auto()
    WHITE_ENGINE_COMBO = auto()
    BLACK_ENGINE_COMBO = auto()
    WHITE_CPU_DURATION = auto()
    BLACK_CPU_DURATION = auto()
    WHITE_CPU_DURATION_TEXT = auto()
    BLACK_CPU_DURATION_TEXT = auto()
    WHITE_CPU_LEVEL_SLIDER = auto()
    BLACK_CPU_LEVEL_SLIDER = auto()
    WHITE_CPU_LEVEL_SLIDER_TEXT = auto()
    BLACK_CPU_LEVEL_SLIDER_TEXT = auto()
    WHITE_NET_LAN_RADIO = auto()
    BLACK_NET_LAN_RADIO = auto()
    WHITE_NET_SERVER_RADIO = auto()
    BLACK_NET_SERVER_RADIO = auto()
    WHITE_NET_RADIO_GROUP = auto()
    BLACK_NET_RADIO_GROUP = auto()
    WHITE_NET_LAN_TABLE = auto()
    BLACK_NET_LAN_TABLE = auto()
    WHITE_NET_SERVER_TEXT = auto()
    BLACK_NET_SERVER_TEXT = auto()
    WHITE_HUMAN = auto()
    BLACK_HUMAN = auto()
    WHITE_CPU = auto()
    BLACK_CPU = auto()
    WHITE_NET = auto()
    BLACK_NET = auto()
    WHITE_TYPE = auto()
    BLACK_TYPE = auto()
    OUTPUT = auto()
    BOARD = auto()
    START = auto()
    ABORD = auto()
    HELP = auto()
    CLAIM = auto()
    NO = auto()
    YES = auto()
    OK = auto()
    ALL_POPUPS = auto()
    ROOK = auto()
    KNIGHT = auto()
    BISHOP = auto()
    QUEEN = auto()
    REPLY_TO_HELP = auto()
    CPU_OR_REMOTE_MOVE = auto()
    NEW_REMOTE_PLAYER = auto()
    CHANGE_OF_REMOTE_GAME_OR_PLAYER_NAME = auto()


class KeyPopup(Enum):  # Keys for the dynamic popups
    CHESSMATE = auto()
    DRAW = auto()
    PROMOTION = auto()


class Draw(IntEnum):  # Types of draws
    STALEMATE = auto()
    THREEFOLD = auto()
    FIVEFOLD = auto()
    FIFTY = auto()
    SEVENTY_FIVE = auto()
    INSUFFICIENT_MATERIAL = auto()


class EngineProtocol(Enum):  # Protocol for communicating with the chess engine
    UCI = auto()
    XBOARD = auto()
    UNKNOWN = auto()


class UCIOptionType(StrEnum):
    CHECK = "check"
    SPIN = "spin"
    COMBO = "combo"
    BUTTON = "button"
    STRING = "string"


class EngineFamily(StrEnum):  # Family of the chess engine
    STOCKFISH = "stockfish"


class DefaultText(StrEnum):  # Default texts displayed on the window
    LOCAL = "local"
    NOT_YET_IMPLEMENTED = "Not yet implemented"
    CURRENT_GAME = "Current game:"
    GAME_NAME = "Game name"
    CURRENT_PLAYER = "Current player:"
    WHITE = "White"
    BLACK = "Black"
    WHITE_PLAYER = "White player"
    BLACK_PLAYER = "Black player"
    PLAYER_NAME = "Player name"
    WHITE_PLAYER_NAME = "White player's name:"
    BLACK_PLAYER_NAME = "Black player's name:"
    ENGINE_TURN_DURATION = "Turn duration (s):"
    SKILL_LEVEL = "Skill level:"
    ELO_LEVEL = "ELO Level:"
    NO_ENGINE_AVAILABLE = "No chess engine available"
    HUMAN = "Human"
    CPU = "CPU"
    NETWORK = "Network"
    START = "Start"
    ABORD = "Abord"
    EXIT = "Exit"
    HELP = "Help"
    NO = "No"
    YES = "Yes"
    OK = "Ok"
    CONFIRM_ABORD = "Do you really want to abord the game ?"
    CONFIRM_EXIT = "Do you really want to exit ?"
    GAME_ENDED = "The game has ended"
    SOMEONE_WINS = "{} wins."
    DRAW = "The game ends in a draw."
    NO_WINNER = "No winner between {} and {}."
    CHESSMATE = "Chessmate"
    STALEMATE = "Stalemate: {} has no possible legal move."
    THREEFOLD = "Threefold repetition: {} claims for an identical position occuring at least three times."
    FIVEFOLD = "Fivefold repetition: an identical position occurs five times."
    FIFTY = "Fifty-move rule: {} claims for no capture or no pawn move occuring in the previous 50 moves."
    SEVENTY_FIVE = "Seventy-five-move rule: no capture or no pawn move has occured in the last 75 moves."
    INSUFFICIENT_MATERIAL = "{} has no sufficient material to win."
    PROMOTION = "Promotion"
    WHAT_PROMOTION = "What piece do you want to promote to ?"
    POWERED_BY = "powered by"
    CLAIM_FOR_THREEFOLD = "Claim for threefold repetition"
    CLAIM_FOR_FIFTY = "Claim for fifty-move rule"
    LAN = "LAN"
    REMOTE_SERVER = "Remote server"
	
class DefaultNetworkPort(IntEnum): # Default network elements
    FINDER_LAN_PORT = 10035 # Listening UDP port of the finder server over the LAN
    GAME_LAN_PORT = 11035 # Listening TCP port of the game server for a LAN game

class DefaultBoardColor(StrEnum):  # Default colors of the board
    LIGHT_SQUARE = "#ffce9e"
    DARK_SQUARE = "#d18b47"
    MARGIN = "#212121"
    COORD = "#e5e5e5"
    START_SQUARE = "#15781b"
    REACHABLE_SQUARE = "#882020"
    ARROW = "#0000cccc"


# Default values
# DEFAULT_WHITE_LOGO_PIECE = "Q"
DEFAULT_WHITE_LOGO_PIECE = random.choice(["P", "N", "B", "R", "Q", "K"])
# DEFAULT_BLACK_LOGO_PIECE = "p"
DEFAULT_BLACK_LOGO_PIECE = random.choice(["p", "n", "b", "r", "q", "k"])
# DEFAULT_ICON_PIECE = "Q"
DEFAULT_ICON_PIECE = random.choice(
    ["P", "N", "B", "R", "Q", "K", "p", "n", "b", "r", "q", "k"]
)
DEFAULT_ICON_SIZE = 32
DEFAULT_LOGO_SIZE = 50
DEFAULT_BOARD_SIZE = 650
ENGINE_PATH = "engines"
RESOURCE_PATH = "resources"
DEFAULT_CURRENT_PLAYER_FILE = "B&WPawn45.svg"
DEFAULT_CURRENT_PLAYER_SIZE = 45
HELP_DURATION = 0.1
DEFAULT_SEARCH_TIME = 1.0  # Default time (in seconds) to search for the next move


# Internal Python-Chess values (to be changed only if Python-Chess changes its own values)
CHESS_DEFAULT_MARGIN_SIZE = 15
CHESS_DEFAULT_SQUARE_SIZE = 45
CHESS_DEFAULT_BOARD_SIZE = 2 * CHESS_DEFAULT_MARGIN_SIZE + 8 * CHESS_DEFAULT_SQUARE_SIZE

# Import submodules
import domichess.display
import domichess.game
import domichess.engine
