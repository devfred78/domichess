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
	Module display: main display management
"""


# Standard modules
# -----------------
from copy import deepcopy
import ctypes
import io
import logging
import pathlib
import random
import subprocess
from threading import Event
from time import sleep

# Third party modules
# --------------------
import cairosvg
import chess, chess.svg, chess.engine
import PySimpleGUI as sg

# Internal modules
# -----------------
from domichess import Result
from domichess import (
    DEFAULT_WHITE_LOGO_PIECE,
    DEFAULT_BLACK_LOGO_PIECE,
    DEFAULT_ICON_PIECE,
    DEFAULT_ICON_SIZE,
    DEFAULT_LOGO_SIZE,
    DEFAULT_BOARD_SIZE,
    CHESS_DEFAULT_MARGIN_SIZE,
    CHESS_DEFAULT_SQUARE_SIZE,
    CHESS_DEFAULT_BOARD_SIZE,
    ENGINE_PATH,
    HELP_DURATION,
    DEFAULT_SEARCH_TIME,
    RESOURCE_PATH,
    DEFAULT_CURRENT_PLAYER_FILE,
    DEFAULT_CURRENT_PLAYER_SIZE,
)
from domichess import (
    Type,
    Key,
    KeyPopup,
    Draw,
    EngineProtocol,
    UCIOptionType,
    EngineFamily,
    DefaultText,
    DefaultBoardColor,
    DefaultNetworkPort,
)
from domichess.game import Player, Game
from domichess.engine import Engine
from domichess.network import opcode, lan, LANFinderServer

# namedtuples
# ------------


# Global constants
# -----------------
Text = DefaultText
BoardColor = DefaultBoardColor
Port = DefaultNetworkPort

# Dataclasses
# ------------

# Classes
# --------


class Display:
    """
    Display class represents what is actually displayed on the screen, and provides tools for managing the interface with the players.

    Display is a singleton, meaning that it can be only instanciated once; multiple instanciation attempts will always return a reference to the same Display object.

    Attributes
    ----------
    board: chess.Board()
            Representation of the position of chess pieces, with move generation.

    Methods
    -------
    """

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      INITIALIZATION
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    def __new__(
        cls, version=None, engine_path=pathlib.Path(ENGINE_PATH).resolve(), logger=None
    ):
        """
        New instance creation (or at least attempt of). As a singleton, verify if there is a previous instance of Display. In such a case, return this instance without creating a new one.

        Inspired from : https://www.geeksforgeeks.org/singleton-pattern-in-python-a-complete-guide/
        """
        if not hasattr(cls, "instance"):
            cls.instance = super(Display, cls).__new__(cls)
        return cls.instance

    def __init__(
        self, version=None, engine_path=pathlib.Path(ENGINE_PATH).resolve(), logger=None
    ):
        """
        Display instance initialization.

        Parameters
        ----------
        version: str, optional
                Current version of DomiChess
        engine_path: pathlib.Path object, optional
                Path where the chess engines are stored. Default is DomiChess.ENGINE_PATH.
        logger : logging.Logger object, optional
                The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.
        """
        if logger is None:
            self.log = logging.getLogger("Display")
            self.log.addHandler(logging.NullHandler())
        else:
            self.log = logger.getChild("Display")

        self.log.debug("--- Display initialization ---")

        # Internal attributes initialization
        self.log.debug("Internal attributes initialization starting...")
        self.version = version
        self._white_logo_piece = DEFAULT_WHITE_LOGO_PIECE  # White logo piece ("P" = pawn, "N" = knight, "B" = bishop, "R" = rook, "Q" = queen, "K" = king)
        self._black_logo_piece = DEFAULT_BLACK_LOGO_PIECE  # White logo piece ("p" = pawn, "n" = knight, "b" = bishop, "r" = rook, "q" = queen, "k" = king)
        self.icon_piece = DEFAULT_ICON_PIECE  # Icon piece
        self._logo_size = DEFAULT_LOGO_SIZE  # logos size, in pixels
        self._icon_size = DEFAULT_ICON_SIZE  # Icon size, in pixels
        self._board_size = DEFAULT_BOARD_SIZE  # Board size, in pixels
        self._board_flipped = False  # True for white at the top and black at the bottom, False (the default) otherwise
        self._engine_path = engine_path
        self.lan_start_game_event = Event()
        self.lan_finder = LANFinderServer(start_game_event=self.lan_start_game_event, port=Port.FINDER_LAN_PORT, logger=self.log) # Players and games finder on the LAN
        self._remote_opponents = {chess.WHITE:[["","",""]], chess.BLACK:[["","",""]]}
		# Images for current player
        with open(
            pathlib.Path(__file__).parent
            / pathlib.Path(RESOURCE_PATH)
            / pathlib.Path(DEFAULT_CURRENT_PLAYER_FILE),
            mode="rt",
        ) as current_neutral_svg_file:
            self._current_neutral_png_bytes = self.svg_to_png_bytes(
                current_neutral_svg_file.read()
            )
        self._current_white_png_bytes = self.svg_to_png_bytes(
            chess.svg.piece(
                chess.Piece.from_symbol(self._white_logo_piece),
                size=DEFAULT_CURRENT_PLAYER_SIZE,
            )
        )
        self._current_black_png_bytes = self.svg_to_png_bytes(
            chess.svg.piece(
                chess.Piece.from_symbol(self._black_logo_piece),
                size=DEFAULT_CURRENT_PLAYER_SIZE,
            )
        )
        # Players
        self._init_players()
        # Engines
        self.engine_list = self._init_engine_list(self._engine_path)
        self.engines = {chess.WHITE: {}, chess.BLACK: {}}
        self.engine_options = {chess.WHITE: {}, chess.BLACK: {}}
        # Engine for help
        if len(self.engine_list) != 0:
            memo = dict()
            if (
                len(self.engine_list) == 1
            ):  # Only one engine: it will be also the helper engine
                self._helper_engine = deepcopy(self.engine_list[0], memo)
            else:
                self._helper_engine = deepcopy(
                    random.choice(self.engine_list), memo
                )  # The helper engine is chosen randomly
            self.log.info(f"{self._helper_engine.name} is the helper engine")
            self._help_engine_caption = f"{self._helper_engine.name}"
            self._helper_engine.search_time = HELP_DURATION
        else:
            self._helper_engine = None
            self.log.warning(
                "No chess engine found. Helper and CPU opponents are unavailable."
            )
            self._help_engine_caption = ""
        self.log.debug("Internal attributes initialized")

        # Board initialization
        self._board = chess.BaseBoard()
        self.board.reset_board()
        self.log.debug("Chessboard initialization")

        # Display initialization
        self._init_display()

        # Popups windows initialization
        self._init_popups()

        self.log.debug("--- Display initialized ---")

    def _init_display(self):
        """
        Display initialization, with associated internal variables.
        """

        # Upper texts and image definition
        game_text = sg.Text(Text.CURRENT_GAME, key=Key.CURRENT_GAME_TEXT)
        game_name = sg.Input(Text.LOCAL, size=20, enable_events=True, key=Key.CURRENT_GAME_NAME)
        player_text = sg.Text(Text.CURRENT_PLAYER, key=Key.CURRENT_PLAYER_TEXT)
        player_name = sg.Text("-", key=Key.CURRENT_PLAYER_NAME)
        player_image = sg.Image(
            self._current_neutral_png_bytes, key=Key.CURRENT_PLAYER_IMAGE
        )

        # logos images definitions
        white_logo_svg_str = chess.svg.piece(
            chess.Piece.from_symbol(self._white_logo_piece), size=self._logo_size
        )
        white_logo_image = self.svg_to_img(white_logo_svg_str, key=Key.WHITE_LOGO)
        black_logo_svg_str = chess.svg.piece(
            chess.Piece.from_symbol(self._black_logo_piece), size=self._logo_size
        )
        black_logo_image = self.svg_to_img(black_logo_svg_str, key=Key.BLACK_LOGO)

        # Engine list caption definition
        engine_caption_list = (
            [engine.name for engine in self.engine_list]
            if len(self.engine_list) != 0
            else None
        )

        # White player tab definition
        # ---------------------------
        # Human tab definition
        white_human_tab = sg.Tab(
            Text.HUMAN,
            [
                [sg.Text(Text.WHITE_PLAYER_NAME)],
                [sg.Input(Text.WHITE_PLAYER, enable_events=True, key=Key.WHITE_NAME)],
            ],
            key=Key.WHITE_HUMAN,
        )
        # CPU tab definition
        if engine_caption_list:
            self.log.debug("Create engines instances for the white player:")
            memo = dict()
            for engine in self.engine_list:
                self.engines[chess.WHITE][engine.name] = deepcopy(engine, memo)
                self.engine_options[chess.WHITE][
                    engine.name
                ] = engine.option.copy_without_engine(memo)
                self.log.debug(f"{engine.name} copied.")
            default_engine = self.engines[chess.WHITE][engine_caption_list[0]]
            white_cpu_combo = sg.Combo(
                engine_caption_list,
                default_value=default_engine.name,
                enable_events=True,
                key=Key.WHITE_ENGINE_COMBO,
                readonly=True,
            )
            white_cpu_duration = sg.Input(
                default_text=DEFAULT_SEARCH_TIME, size=5, key=Key.WHITE_CPU_DURATION
            )
            white_slider_is_invisible = False
            if "UCI_Elo" in default_engine.engine_options:
                if "UCI_LimitStrength" in default_engine.engine_options:
                    if not self.engine_options[chess.WHITE][
                        default_engine.name
                    ].UCI_LimitStrength():
                        self.engine_options[chess.WHITE][
                            default_engine.name
                        ].UCI_LimitStrength = True
                white_cpu_level_slider_text = sg.Text(
                    Text.ELO_LEVEL, key=Key.WHITE_CPU_LEVEL_SLIDER_TEXT, visible=True
                )
                white_cpu_level_slider = sg.Slider(
                    range=(
                        self.engine_options[chess.WHITE][
                            default_engine.name
                        ].UCI_LimitStrength.min,
                        self.engine_options[chess.WHITE][
                            default_engine.name
                        ].UCI_LimitStrength.max,
                    ),
                    default_value=self.engine_options[chess.WHITE][
                        default_engine.name
                    ].UCI_LimitStrength.default,
                    orientation="horizontal",
                    enable_events=True,
                    key=Key.WHITE_CPU_LEVEL_SLIDER,
                    disabled=False,
                    visible=True,
                )
            else:
                white_slider_is_invisible = True
                white_cpu_level_slider_text = sg.Text(
                    "NOTHING", key=Key.WHITE_CPU_LEVEL_SLIDER_TEXT, visible=True
                )
                white_cpu_level_slider = sg.Slider(
                    range=(0, 2),
                    default_value=1,
                    orientation="horizontal",
                    enable_events=True,
                    key=Key.WHITE_CPU_LEVEL_SLIDER,
                    disabled=False,
                    visible=True,
                )
            white_computer_tab = sg.Tab(
                Text.CPU,
                [
                    [
                        white_cpu_combo,
                        sg.Push(),
                        sg.Text(
                            Text.ENGINE_TURN_DURATION, key=Key.WHITE_CPU_DURATION_TEXT
                        ),
                        white_cpu_duration,
                    ],
                    [sg.pin(white_cpu_level_slider_text, shrink=False), sg.Push()],
                    [sg.pin(white_cpu_level_slider, shrink=False)],
                ],
                key=Key.WHITE_CPU,
            )
        else:
            white_computer_tab = sg.Tab(
                Text.CPU, [[sg.Text(Text.NO_ENGINE_AVAILABLE)]], key=Key.WHITE_CPU
            )
        # Network tab definition
        white_net_lan_radio = sg.Radio(text=Text.LAN, group_id=Key.WHITE_NET_RADIO_GROUP, default=True, enable_events=True, key=Key.WHITE_NET_LAN_RADIO)
        white_net_server_radio = sg.Radio(text=Text.REMOTE_SERVER, group_id=Key.WHITE_NET_RADIO_GROUP, default=False, enable_events=True, key=Key.WHITE_NET_SERVER_RADIO)
        
        white_net_lan_table = sg.Table(values=self._remote_opponents[chess.WHITE], headings=[Text.PLAYER_NAME, Text.GAME_NAME, Text.INVITING], max_col_width=25, auto_size_columns=True, num_rows=3, vertical_scroll_only=True, enable_events=True, justification="left", key=Key.WHITE_NET_LAN_TABLE)

        white_net_server_text = sg.Text(text=Text.NOT_YET_IMPLEMENTED, key=Key.WHITE_NET_SERVER_TEXT, visible=False)
        
        white_network_tab = sg.Tab(Text.NETWORK,
            [[white_net_lan_radio, white_net_server_radio],
            [white_net_lan_table, white_net_server_text]],
            key=Key.WHITE_NET)

        # Tabgroup definition
        white_tab = sg.TabGroup(
            [[white_human_tab, white_computer_tab, white_network_tab]],
            key=Key.WHITE_TYPE,
            enable_events=True,
        )

        # Black player tab definition
        # ---------------------------
        # Human tab definition
        black_human_tab = sg.Tab(
            Text.HUMAN,
            [
                [sg.Text(Text.BLACK_PLAYER_NAME)],
                [sg.Input(Text.BLACK_PLAYER, enable_events=True, key=Key.BLACK_NAME)],
            ],
            key=Key.BLACK_HUMAN,
        )
        # CPU tab definition
        if engine_caption_list:
            self.log.debug("Create engines instances for the black player:")
            memo = dict()
            for engine in self.engine_list:
                self.engines[chess.BLACK][engine.name] = deepcopy(engine, memo)
                self.engine_options[chess.BLACK][
                    engine.name
                ] = engine.option.copy_without_engine(memo)
                self.log.debug(f"{engine.name} copied.")
            default_engine = self.engines[chess.BLACK][engine_caption_list[0]]
            black_cpu_combo = sg.Combo(
                engine_caption_list,
                default_value=default_engine.name,
                enable_events=True,
                key=Key.BLACK_ENGINE_COMBO,
                readonly=True,
            )
            black_cpu_duration = sg.Input(
                default_text=DEFAULT_SEARCH_TIME, size=5, key=Key.BLACK_CPU_DURATION
            )
            black_slider_is_invisible = False
            if "UCI_Elo" in default_engine.engine_options:
                if "UCI_LimitStrength" in default_engine.engine_options:
                    if not self.engine_options[chess.BLACK][
                        default_engine.name
                    ].UCI_LimitStrength():
                        self.engine_options[chess.BLACK][
                            default_engine.name
                        ].UCI_LimitStrength = True
                black_cpu_level_slider_text = sg.Text(
                    Text.ELO_LEVEL, key=Key.BLACK_CPU_LEVEL_SLIDER_TEXT, visible=True
                )
                black_cpu_level_slider = sg.Slider(
                    range=(
                        self.engine_options[chess.BLACK][
                            default_engine.name
                        ].UCI_LimitStrength.min,
                        self.engine_options[chess.BLACK][
                            default_engine.name
                        ].UCI_LimitStrength.max,
                    ),
                    default_value=self.engine_options[chess.BLACK][
                        default_engine.name
                    ].UCI_LimitStrength.default,
                    orientation="horizontal",
                    enable_events=True,
                    key=Key.BLACK_CPU_LEVEL_SLIDER,
                    disabled=False,
                    visible=True,
                )
            else:
                black_slider_is_invisible = True
                black_cpu_level_slider_text = sg.Text(
                    "NOTHING", key=Key.BLACK_CPU_LEVEL_SLIDER_TEXT, visible=True
                )
                black_cpu_level_slider = sg.Slider(
                    range=(0, 2),
                    default_value=1,
                    orientation="horizontal",
                    enable_events=True,
                    key=Key.BLACK_CPU_LEVEL_SLIDER,
                    disabled=False,
                    visible=True,
                )
            black_computer_tab = sg.Tab(
                Text.CPU,
                [
                    [
                        black_cpu_combo,
                        sg.Push(),
                        sg.Text(
                            Text.ENGINE_TURN_DURATION, key=Key.BLACK_CPU_DURATION_TEXT
                        ),
                        black_cpu_duration,
                    ],
                    [sg.pin(black_cpu_level_slider_text, shrink=False), sg.Push()],
                    [sg.pin(black_cpu_level_slider, shrink=False)],
                ],
                key=Key.BLACK_CPU,
            )
        else:
            black_computer_tab = sg.Tab(
                Text.CPU, [[sg.Text(Text.NO_ENGINE_AVAILABLE)]], key=Key.BLACK_CPU
            )
        # Network tab definition
        black_net_lan_radio = sg.Radio(text=Text.LAN, group_id=Key.BLACK_NET_RADIO_GROUP, default=True, enable_events=True, key=Key.BLACK_NET_LAN_RADIO)
        black_net_server_radio = sg.Radio(text=Text.REMOTE_SERVER, group_id=Key.BLACK_NET_RADIO_GROUP, default=False, enable_events=True, key=Key.BLACK_NET_SERVER_RADIO)
        
        black_net_lan_table = sg.Table(values=self._remote_opponents[chess.BLACK], headings=[Text.PLAYER_NAME, Text.GAME_NAME, Text.INVITING], max_col_width=25, auto_size_columns=True, num_rows=3, vertical_scroll_only=True, enable_events=True, justification="left", key=Key.BLACK_NET_LAN_TABLE)

        black_net_server_text = sg.Text(text=Text.NOT_YET_IMPLEMENTED, key=Key.BLACK_NET_SERVER_TEXT, visible=False)
        
        black_network_tab = sg.Tab(Text.NETWORK,
            [[black_net_lan_radio, black_net_server_radio],
            [black_net_lan_table, black_net_server_text]],
            key=Key.BLACK_NET)
			
        # Tabgroup definition
        black_tab = sg.TabGroup(
            [[black_human_tab, black_computer_tab, black_network_tab]],
            key=Key.BLACK_TYPE,
            enable_events=True,
        )

        # Frames definitions
        white_frame = sg.Frame(
            Text.WHITE_PLAYER,
            [[sg.vtop(sg.Column([[white_logo_image]])), sg.VSep(), white_tab]],
        )
        black_frame = sg.Frame(
            Text.BLACK_PLAYER,
            [[sg.vtop(sg.Column([[black_logo_image]])), sg.VSep(), black_tab]],
        )

        # Output panel definition
        output_panel = sg.Multiline(
            autoscroll=True,
            size=(60, 13),
            key=Key.OUTPUT,
            reroute_cprint=True,
            disabled=True,
        )

        # board image definition
        self._board_color = {
            "square_light": BoardColor.LIGHT_SQUARE,
            "square dark": BoardColor.DARK_SQUARE,
            "margin": BoardColor.MARGIN,
            "coord": BoardColor.COORD,
        }
        board_svg_str = chess.svg.board(
            self._board,
            size=self._board_size,
            colors=self._board_color,
            flipped=self._board_flipped,
        )
        board_image = self.svg_to_img(board_svg_str, key=Key.BOARD, enable_events=True)

        # General buttons definition
        start_button = sg.Button(
            Text.START, button_color=("white", "green"), key=Key.START
        )
        abord_button = sg.Button(
            Text.ABORD, button_color=("white", "red"), key=Key.ABORD, visible=False
        )
        help_button = sg.Button(
            Text.HELP, button_color=("white", "green"), key=Key.HELP, visible=False
        )
        claim_button = sg.Button(
            Text.CLAIM_FOR_THREEFOLD,
            button_color=("white", "orange"),
            key=Key.CLAIM,
            visible=False,
        )

        # layout definition
        layout = [
            [
                sg.vtop(
                    sg.Column(
                        [
                            [
                                game_text,
                                game_name,
                                sg.Push(),
                                sg.Column(
                                    [
                                        [player_text, player_image],
                                        [sg.Push(), player_name, sg.Push()],
                                    ]
                                ),
                            ],
                            [white_frame],
                            [black_frame],
                            [start_button, abord_button, help_button, claim_button],
                            [output_panel],
                        ]
                    )
                ),
                sg.VSep(),
                board_image,
            ]
        ]

        # icon definition
        icon_svg_str = chess.svg.piece(
            chess.Piece.from_symbol(self.icon_piece), size=self._icon_size
        )
        icon = self.svg_to_png_bytes(icon_svg_str)

        # Window definition
        self.log.debug(
            f"Attempt to create the main window: DomiChess {self.version if self.version else ''} {Text.POWERED_BY if self._helper_engine else ''} {self._help_engine_caption}"
        )
        self._window = sg.Window(
            f"DomiChess {self.version if self.version else ''} {Text.POWERED_BY if self._helper_engine else ''} {self._help_engine_caption}",
            layout,
            icon=icon,
            finalize=True,
            enable_close_attempted_event=True,
        )
        if engine_caption_list:
            if white_slider_is_invisible:
                self._window[Key.WHITE_CPU_LEVEL_SLIDER_TEXT].update(visible=False)
                self._window[Key.WHITE_CPU_LEVEL_SLIDER].update(
                    disabled=True, visible=False
                )
            if black_slider_is_invisible:
                self._window[Key.BLACK_CPU_LEVEL_SLIDER_TEXT].update(visible=False)
                self._window[Key.BLACK_CPU_LEVEL_SLIDER].update(
                    disabled=True, visible=False
                )

        if len(self.engine_list) == 0:
            self._window[Key.WHITE_CPU].update(disabled=True)
            self._window[Key.BLACK_CPU].update(disabled=True)
        
        # bind tkiner events
        board_image.bind("<Button-1>", "_left_click")

        # Welcome message
        sg.cprint(f"Welcome in DomiChess {self.version if self.version else ''} !")
        if len(self.engine_list) != 0:
            sg.cprint(
                f"Chess engine{'s' if len(self.engine_list) > 0 else ''} found:",
                end=" ",
                t="green",
            )
            for rank, engine in enumerate(self.engine_list):
                if rank < len(self.engine_list) - 1:
                    sg.cprint(f"{engine.name}", end=", ", t="green")
                else:
                    sg.cprint(f"{engine.name}", t="green")
            sg.cprint(f"{self._helper_engine.name} is the helper engine", t="green")
        else:
            sg.cprint(
                "No chess engine found. Helper and CPU opponents are unavailable.",
                t="orange",
            )

    def _init_popups(self, key=Key.ALL_POPUPS):
        """
        Initializes popups windows.
        """
        if key == Key.ALL_POPUPS or key == sg.WINDOW_CLOSE_ATTEMPTED_EVENT:
            self._confirm_exit_popup = sg.Window(
                Text.EXIT,
                [
                    [sg.Text(Text.CONFIRM_EXIT)],
                    [sg.Yes(Text.YES, key=Key.YES), sg.No(Text.NO, key=Key.NO)],
                ],
                disable_minimize=True,
                modal=True,
            )
        if key == Key.ALL_POPUPS or key == Key.ABORD:
            self._confirm_abord_popup = sg.Window(
                Text.ABORD,
                [
                    [sg.Text(Text.CONFIRM_ABORD)],
                    [sg.Yes(Text.YES, key=Key.YES), sg.No(Text.NO, key=Key.NO)],
                ],
                disable_minimize=True,
                modal=True,
            )
        if key == Key.ALL_POPUPS or key == Key.BOARD + "_left_click":
            pass

    def _init_before_start(self):
        """
        Initializes or re-iniitializes the state of the attributes to be ready to start (or re-start) a new game.
        """
        self._window[Key.START].update(disabled=False)
        self._window[Key.ABORD].update(visible=False, disabled=True)
        self._window[Key.HELP].update(visible=False, disabled=True)
        self._window[Key.CLAIM].update(visible=False, disabled=True)
        self._window[Key.WHITE_NAME].update(disabled=False)
        self._window[Key.WHITE_HUMAN].update(disabled=False)
        if len(self.engine_list) == 0:
            self._window[Key.WHITE_CPU].update(disabled=True)
        else:
            self._window[Key.WHITE_CPU].update(disabled=False)
        self._window[Key.WHITE_NET].update(disabled=False)
        self._window[Key.BLACK_NAME].update(disabled=False)
        self._window[Key.BLACK_HUMAN].update(disabled=False)
        if len(self.engine_list) == 0:
            self._window[Key.BLACK_CPU].update(disabled=True)
        else:
            self._window[Key.BLACK_CPU].update(disabled=False)
        self._window[Key.BLACK_NET].update(disabled=False)

        self._window[Key.CURRENT_GAME_NAME].update(disabled=False)
        self._window[Key.CURRENT_PLAYER_NAME].update("-")
        self._window[Key.CURRENT_PLAYER_IMAGE].update(self._current_neutral_png_bytes)

        self.board = chess.BaseBoard()
        self._draw_claimed = None
        
        self._init_players()

    def _init_engine_list(self, engine_path):
        """
        Initializes the list of the available engines.

        Parameters
        ----------
        engine_path: pathlib.Path object, mandatory
                Path where the chess engines are stored.

        Returns
        -------
        A list of domichess.engine.Engine object represnting the available engines
        """
        engine_list = []
        engine_path_list = [
            item
            for item in engine_path.iterdir()
            if (item.is_file() and (item.suffix.lower() == ".exe"))
        ]
        for engine_exe in engine_path_list:
            try:
                engine = Engine(engine_exe, self.log)
                if engine.protocol != EngineProtocol.UNKNOWN:
                    engine_list.append(engine)
            except ValueError:
                pass
        if len(engine_list) == 0:
            self.log.warning("No chess engine available")
        return engine_list

    def _init_players(self):
        """
        Initializes white and black Players instances (attribute `players`).
        
        Players are instanciated as human opponents first, and can be modified later.
        """
        self._players = {chess.WHITE:Player(name=Text.WHITE_PLAYER, color=chess.WHITE, type=Type.HUMAN, logger=self.log), chess.BLACK:Player(name=Text.BLACK_PLAYER, color=chess.BLACK, type=Type.HUMAN, logger=self.log)}
        

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      ATTRIBUTES
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    #####################################
    # Class attributes

    #####################################
    # Private attributes

    #####################################
    # Public attributes

    @property
    def players(self):
        """
        White and black Players instances.
        
        This attribute is a dictionnary of 2 elements, keyed by `chess.WHITE` and `chess.BLACK`, and valued by `Player` objects.
        """
        return _players
    
    @players.setter
    def players(self, value):
        if not isinstance(value, dict):
            raise TypeError("`players` must be a dictionnary.")
        elif len(value) != 2:
            raise ValueError("`players` must be setted with exactly 2 elements.")
        elif (chess.WHITE not in value) or (chess.BLACK not in value):
            raise ValueError("`players` must be keyed by `chess.WHITE` and `chess.BLACK`.")
        elif (not isinstance(value[chess.WHITE], Player)) or (not isinstance(value[chess.BLACK], Player)):
            raise ValueError("`players` must be valued by Player instances only.")
        else:
            _players = value
        
    
    @property
    def board_flipped(self):
        """
        orientation of the rendered board.

        This is a boolean value: False for a "normal" rendering (black at the top and white at the bottom of the displayed board), and True for a reversed view (white at the top and black at the bottom).

        When set, the board displayed is also modified to reflect the change.
        """
        return self._board_flipped

    @board_flipped.setter
    def board_flipped(self, value):
        if not isinstance(value, bool):
            raise ValueError("board_flipped must be a boolean.")
        else:
            self._board_flipped = value
            board_svg_str = chess.svg.board(
                self.board, size=self._board_size, flipped=self._board_flipped
            )
            png_bytes = self.svg_to_png_bytes(board_svg_str)
            self._window[Key.BOARD].update(source=png_bytes)

    @property
    def board(self):
        """
        chess.BaseBoard object representing the rendered board.

        Whet set, the display is updated to reflect the (potential) changes.
        """
        return self._board

    @board.setter
    def board(self, value):
        if not isinstance(value, chess.BaseBoard):
            raise ValueError("board must be a chess.BaseBoard object")
        else:
            self._board = value
            board_svg_str = chess.svg.board(
                self._board, size=self._board_size, flipped=self.board_flipped
            )
            png_bytes = self.svg_to_png_bytes(board_svg_str)
            self._window[Key.BOARD].update(source=png_bytes)

    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
    #
    #      METHODS
    #
    # *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

    #####################################
    # Class methods

    #####################################
    # static methods

    @staticmethod
    def svg_to_png_bytes(svg_str):
        """
        Converts Scalable Vector Graphic (SVG) string into a PNG format in a base64 byte object.

        Parameters
        ----------
        svg_str: string, mandatory
                SVG image description

        Returns
        -------
        The PNG base64 byte object corresponding to the SVG.
        """

        # string to file-like object conversion
        svg_io = io.StringIO(svg_str)

        # svg to png conversion, into a base64 byte object
        png_str = cairosvg.svg2png(file_obj=svg_io)
        png_io_file = io.BytesIO(png_str)
        png_bytes = png_io_file.read()

        return png_bytes

    @staticmethod
    def svg_to_img(svg_str, key, enable_events=False):
        """
        Converts Scalable Vector Graphic (SVG) string into pySimpleGUI Image element.

        Parameters
        ----------
        svg_str: string, mandatory
                SVG image description
        key: string, mandatory
                key of the pySimpleGUI Image object
        enable_events: boolean, optional
                ability of the pySimpleGUI Image element to send events (the default is False)

        Returns
        -------
        The pySimpleGUI Image element corresponding to the SVG.
        """

        # string to file-like object conversion
        svg_io = io.StringIO(svg_str)

        # svg to png conversion, into a base64 byte object
        png_str = cairosvg.svg2png(file_obj=svg_io)
        png_io_file = io.BytesIO(png_str)
        png_bytes = png_io_file.read()

        # Surface generation
        return sg.Image(source=png_bytes, key=key, enable_events=enable_events)

    #####################################
    # Private methods

    def _dyn_popup(self, key_popup, params):
        """
        Creates and displays a popup, modal window, with personnalized parameters.

        Parameters
        ----------
        key_popup: KeyPopup object, mandatory
                identification of the popup to display
        params: dict, mandatory
                parameters for personnalization of the popup to display. The possible keys depend on the given key_popup:
                        key_popup = KeyPopup.CHESSMATE:
                                'winner': chess.WHITE or chess.BLACK
                                'name_winner': str, name of the winner
                        key_popup = KeyPopup.PROMOTION:
                                'player': chess.WHITE or chess.BLACK, player to be promoted
                        key_popup = KeyPopup.DRAW:
                                'draw': domichess.Draw object, type of draw
                                'player': str, name of the player implied in the draw. Depends on the type of draw:
                                        Draw.STALEMATE: name of the player who has no possible legal move
                                        Draw.THREEFOLD: name of the player who claims for a repetition of three identical positions
                                        Draw.FIFTY: name of the player who claims for no capture or no pawn move in the previous 50 moves
                                        Draw.INSUFFICIENT_MATERIAL: name of the player who has no sufficient material to win
                                        Not relevant for the other cases

        Returns
        -------
        (event, values), the result of the sg.Window object.
        """

        if key_popup == KeyPopup.CHESSMATE:
            self.log.debug("displaying chessmate popup.")
            if params["winner"] == chess.WHITE:
                logo_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol(self._white_logo_piece),
                    size=self._logo_size,
                )
                logo_image = self.svg_to_img(logo_svg_str, key=Key.WHITE_LOGO)
            else:
                logo_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol(self._black_logo_piece),
                    size=self._logo_size,
                )
                logo_image = self.svg_to_img(logo_svg_str, key=Key.BLACK_LOGO)
            result = sg.Window(
                Text.GAME_ENDED,
                [
                    [
                        logo_image,
                        sg.Column(
                            [
                                [sg.Text(Text.CHESSMATE)],
                                [
                                    sg.Text(
                                        Text.SOMEONE_WINS.format(params["name_winner"])
                                    )
                                ],
                            ]
                        ),
                    ],
                    [sg.Push(), sg.Ok(Text.OK, key=Key.OK), sg.Push()],
                ],
                disable_minimize=True,
                modal=True,
            ).read(close=True)
        elif key_popup == KeyPopup.DRAW:
            self.log.debug("displaying draw popup.")
            white_logo_svg_str = chess.svg.piece(
                chess.Piece.from_symbol(self._white_logo_piece), size=self._logo_size
            )
            white_logo_image = self.svg_to_img(white_logo_svg_str, key=Key.WHITE_LOGO)
            black_logo_svg_str = chess.svg.piece(
                chess.Piece.from_symbol(self._black_logo_piece), size=self._logo_size
            )
            black_logo_image = self.svg_to_img(black_logo_svg_str, key=Key.BLACK_LOGO)
            if params["draw"] == Draw.STALEMATE:
                text_to_display = Text.STALEMATE.format(params["player"])
            elif params["draw"] == Draw.THREEFOLD:
                text_to_display = Text.THREEFOLD.format(params["player"])
            elif params["draw"] == Draw.FIVEFOLD:
                text_to_display = Text.FIVEFOLD
            elif params["draw"] == Draw.FIFTY:
                text_to_display = Text.FIFTY.format(params["player"])
            elif params["draw"] == Draw.SEVENTY_FIVE:
                text_to_display = Text.SEVENTY_FIVE
            elif params["draw"] == Draw.INSUFFICIENT_MATERIAL:
                text_to_display = Text.INSUFFICIENT_MATERIAL.format(params["player"])
            else:
                text_to_display = ""
            result = sg.Window(
                Text.GAME_ENDED,
                [
                    [
                        white_logo_image,
                        black_logo_image,
                        sg.Column([[sg.Text(Text.DRAW)], [sg.Text(text_to_display)]]),
                    ],
                    [sg.Push(), sg.Ok(Text.OK, key=Key.OK), sg.Push()],
                ],
                disable_minimize=True,
                modal=True,
            ).read(close=True)
        elif key_popup == KeyPopup.PROMOTION:
            self.log.debug("displaying promotion popup.")
            if params["player"] == chess.WHITE:
                rook_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("R"), size=self._logo_size
                )
                knight_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("N"), size=self._logo_size
                )
                bishop_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("B"), size=self._logo_size
                )
                queen_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("Q"), size=self._logo_size
                )
            else:
                rook_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("r"), size=self._logo_size
                )
                knight_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("n"), size=self._logo_size
                )
                bishop_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("b"), size=self._logo_size
                )
                queen_svg_str = chess.svg.piece(
                    chess.Piece.from_symbol("q"), size=self._logo_size
                )
            rook_image = self.svg_to_img(rook_svg_str, key=Key.ROOK, enable_events=True)
            knight_image = self.svg_to_img(
                knight_svg_str, key=Key.KNIGHT, enable_events=True
            )
            bishop_image = self.svg_to_img(
                bishop_svg_str, key=Key.BISHOP, enable_events=True
            )
            queen_image = self.svg_to_img(
                queen_svg_str, key=Key.QUEEN, enable_events=True
            )
            result = sg.Window(
                Text.PROMOTION,
                [
                    [sg.Push(), sg.Text(Text.WHAT_PROMOTION), sg.Push()],
                    [
                        sg.Push(),
                        rook_image,
                        knight_image,
                        bishop_image,
                        queen_image,
                        sg.Push(),
                    ],
                ],
                disable_minimize=True,
                modal=True,
            ).read(close=True)

        return result

    def _coord_to_square(self, coord):
        """
        Converts coordinates into a chess.Square object.

        This method analyzes the given iterable of 2 integers, expecting they represents the coordinates (x,y) of a pixel in the board represntation on the GUI. If the pixel is inside a square of the board, the method returns the corresponding chess.Square object. Otherwise it returns None.

        Parameters
        ----------
        coord: iterable of 2 integers

        Returns
        -------
        A chess.Square object or None
        """

        if len(coord) != 2:
            raise ValueError("coord must be an iterable of 2 integers.")
        elif not isinstance(coord[0], int):
            raise ValueError("The first coordinate is not an integer.")
        elif not isinstance(coord[1], int):
            raise ValueError("The second coordinate is not an integer.")

        x = coord[0]
        y = coord[1]

        current_margin_size = int(
            CHESS_DEFAULT_MARGIN_SIZE * self._board_size / CHESS_DEFAULT_BOARD_SIZE
        )
        current_square_size = int(
            CHESS_DEFAULT_SQUARE_SIZE * self._board_size / CHESS_DEFAULT_BOARD_SIZE
        )

        # File (column) calculation
        if (x < current_margin_size) or (
            x > (current_margin_size + 8 * current_square_size)
        ):
            return None
        else:
            if self._board_flipped:
                file = 7 - (x - current_margin_size) // current_square_size
            else:
                file = (x - current_margin_size) // current_square_size

        # Rank (row) calculation
        if (y < current_margin_size) or (
            y > (current_margin_size + 8 * current_square_size)
        ):
            return None
        else:
            if self._board_flipped:
                rank = (y - current_margin_size) // current_square_size
            else:
                rank = 7 - (y - current_margin_size) // current_square_size

        return chess.square(file, rank)

    def _prepare_game(self, white_name, white_type, black_name, black_type, values):
        """
        Prepares a game to start.

        Parameters
        ----------
        white_name: str, mandatory
                Name of the white player
        white_type: domichess.Key, mandatory
                Type of the white player. Possible values: Key.WHITE_HUMAN, Key.WHITE_CPU, Key.WHITE_NET. Other value is replaced automatically by Key.WHITE_HUMAN
        black_name: str, mandatory
                Name of the black player
        black_type: domichess.Key, mandatory
                Type of the black player. Possible values: Key.BLACK_HUMAN, Key.BLACK_CPU, Key.BLACK_NET. Other value is replaced automatically by Key.BLACK_HUMAN
        values: dict, mandatory
                values returned by the last self._window.read(), to pick some extra contextual values if necessary

        Returns
        -------
        A Domichess.game.Game object, representing the starting game.
        """

        # White player
        if white_type == Key.WHITE_HUMAN:
            type = Type.HUMAN
        elif white_type == Key.WHITE_CPU:
            type = Type.CPU
            original_engine = [
                engine
                for engine in self.engine_list
                if engine.name == values[Key.WHITE_ENGINE_COMBO]
            ][0]
            memo = dict()
            self.engines[chess.WHITE][values[Key.WHITE_ENGINE_COMBO]] = deepcopy(
                original_engine, memo
            )
            self._apply_engine_options(
                self.engine_options[chess.WHITE][values[Key.WHITE_ENGINE_COMBO]],
                self.engines[chess.WHITE][values[Key.WHITE_ENGINE_COMBO]],
            )

        elif white_type == Key.WHITE_NET:
            type = Type.NETWORK
        else:
            type = Type.HUMAN
        self._players[chess.WHITE].name = white_name
        self._players[chess.WHITE].color = chess.WHITE
        self._players[chess.WHITE].type = type

        # Black player
        if black_type == Key.BLACK_HUMAN:
            type = Type.HUMAN
        elif black_type == Key.BLACK_CPU:
            type = Type.CPU
            original_engine = [
                engine
                for engine in self.engine_list
                if engine.name == values[Key.BLACK_ENGINE_COMBO]
            ][0]
            memo = dict()
            self.engines[chess.BLACK][values[Key.BLACK_ENGINE_COMBO]] = deepcopy(
                original_engine, memo
            )
            self._apply_engine_options(
                self.engine_options[chess.BLACK][values[Key.BLACK_ENGINE_COMBO]],
                self.engines[chess.BLACK][values[Key.BLACK_ENGINE_COMBO]],
            )
        elif black_type == Key.BLACK_NET:
            type = Type.NETWORK
        else:
            type = Type.HUMAN
        self._players[chess.BLACK].name = black_name
        self._players[chess.BLACK].color = chess.BLACK
        self._players[chess.BLACK].type = type

        # Initialize other attributes
        self._reachable_squares = ()

        # New game for the helper engine
        if self._helper_engine is not None:
            self._helper_engine.start_new_game(name=values[Key.CURRENT_GAME_NAME])

        # Game
        return Game(
            name=values[Key.CURRENT_GAME_NAME],
            white_player=self._players[chess.WHITE],
            black_player=self._players[chess.BLACK],
            helper_engine=self._helper_engine,
            logger=self.log,
        )

    def _update_cpu_tab(self, player, engine_name):
        """
        Updates the CPU tab display for the concerned player after changing the current engine.

        Parameters
        ----------
        player: chess.Color object, mandatory
                The concerned player (chess.WHITE or chess.BLACK)
        engine_name: str, mandatory
                the name of the new, selected engine

        Returns
        -------
        None
        """
        if player == chess.WHITE:
            KEY_CPU_LEVEL_SLIDER_TEXT = Key.WHITE_CPU_LEVEL_SLIDER_TEXT
            KEY_CPU_LEVEL_SLIDER = Key.WHITE_CPU_LEVEL_SLIDER
        else:
            KEY_CPU_LEVEL_SLIDER_TEXT = Key.BLACK_CPU_LEVEL_SLIDER_TEXT
            KEY_CPU_LEVEL_SLIDER = Key.BLACK_CPU_LEVEL_SLIDER
        if "UCI_Elo" in self.engines[player][engine_name].engine_options:
            if "UCI_LimitStrength" in self.engines[player][engine_name].engine_options:
                if not self.engine_options[player][engine_name].UCI_LimitStrength():
                    self.engine_options[player][engine_name].UCI_LimitStrength = True
            self._window[KEY_CPU_LEVEL_SLIDER_TEXT].update(
                value=Text.ELO_LEVEL, visible=True
            )
            self._window[KEY_CPU_LEVEL_SLIDER].update(
                value=self.engine_options[player][engine_name].UCI_Elo(),
                range=(
                    self.engine_options[player][engine_name].UCI_Elo.min,
                    self.engine_options[player][engine_name].UCI_Elo.max,
                ),
                disabled=False,
                visible=True,
            )
        else:
            self._window[KEY_CPU_LEVEL_SLIDER_TEXT].update(visible=False)
            self._window[KEY_CPU_LEVEL_SLIDER].update(disabled=True, visible=False)

    def _update_lan_table(self, color:bool):
        """
        Updates the table of potential remote opponents on the LAN, for the given color.
        
        Parameters:
            color:
                True for the opponents of the white player, False for the opponents of the black player
        """
        if self.lan_finder.started:
            opponents = list()
            for lan_player in self.lan_finder.rem_players.values():
                if lan_player[lan.PLAYERCOLOR] != color:
                    opponents.append([lan_player[lan.PLAYERNAME],lan_player[lan.GAMENAME],"X" if lan_player[lan.INVITING] else ""])
            if len(opponents) == 0:
                opponents = [["","",""]]
        else:
            opponents = [["","",""]]

        if color == chess.WHITE:
            self._window[Key.BLACK_NET_LAN_TABLE].update(values=opponents)
            self.log.debug("The LAN black table is updated")
        else:
            self._window[Key.WHITE_NET_LAN_TABLE].update(values=opponents)
            self.log.debug("The LAN white table is updated")
        
        self._remote_opponents[color] = opponents
        self.log.debug(f"The updated list of the remote opponents known at the display level is: {self._remote_opponents}")

    def _apply_engine_options(self, options, engine):
        """
        Applies options to a chess Engine. If the engine has not a particular option, it is silently ignored.

        Parameters
        ----------
        options: domichess.engigne,Options object, mandatory
                Options to apply
        engine: domichess.engine.Engine object, mandatory
                the engine on which the options are applied

        Returns
        -------
        None
        """
        for option in dir(options):
            if hasattr(engine.option, option):
                if getattr(engine.option, option)() != getattr(options, option)():
                    getattr(engine.option, option).value = getattr(options, option)()

    def _wait_for_new_remote_LAN_player(self):
        """
        Waits until a new remote player is available on the LAN.
        """
        self.log.debug("Waiting for a new available remote player...")
        nb_remote_lan_players = len(self.lan_finder.rem_players)
        while self.lan_finder.started:
            if len(self.lan_finder.rem_players) > nb_remote_lan_players:
                self.log.debug("A new remote, LAN player is detected !")
                break
            elif len(self.lan_finder.rem_players) < nb_remote_lan_players:
                self.log.debug("A remote player has leaved the network !")
                nb_remote_lan_players = len(self.lan_finder.rem_players)
            sleep(0.1) # To avoid to overload CPU
        if not self.lan_finder.started:
            self.log.debug("LAN finder server stopped: no more wait for a new remote player")
    
    def _wait_for_change_remote_game_or_player_name(self) -> bool|None:
        """
        Waits until a remote game or player's name has changed.
        
        Returns:
            chess.WHITE if a change is detected among opponents of the white player, or chess.BLACK if a change is detected among opponents of the black player
        """
        self.log.debug("Waiting for a change of a remote game or player's name...")
        change = "no"
        while self.lan_finder.started:
            for color in [chess.WHITE, chess.BLACK]:
                opponents = list()
                for lan_player in self.lan_finder.rem_players.values():
                    if lan_player[lan.PLAYERCOLOR] != color:
                        opponents.append([lan_player[lan.PLAYERNAME],lan_player[lan.GAMENAME],"X" if lan_player[lan.INVITING] else ""])
                if len(opponents) == 0:
                    opponents = [["","",""]]
                if opponents != self._remote_opponents[color]:
                    if color == chess.WHITE:
                        change = "white"
                        self.log.debug("A change has been detected among the opponents of the white player")
                    elif color == chess.BLACK:
                        change = "black"
                        self.log.debug("A change has been detected among the opponents of the black player")
                    else:
                        pass
            if change in ["white", "black"]:
                break
            sleep(0.1) # To avoid to overload CPU
        
        if change == "white":
            return chess.WHITE
        elif change == "black":
            return chess.BLACK
        else: # The LAN finder is stopped
            self.log.debug("LAN finder server stopped: no more wait for a change of a remote game or player's name")
        
        
    #####################################
    # Public methods

    def start_display(self):
        """
        Starts the loop display. Blocks until the loop_stop_event Event is set.

        Parameters
        ----------
        None.
        """

        # Display loop
        while True:
            event, values = self._window.read()
            if event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT:  # Close the application
                if self._confirm_exit_popup.read(close=True)[0] == Key.YES:
                    if hasattr(self, "_game"):
                        self._game.ongoing = False
                    self.log.debug("Stop the white engine instances:")
                    self.log.debug("--------------------------------")
                    for engine in self.engines[chess.WHITE].values():
                        if engine is not None:
                            engine.quit()
                            try:
                                self.log.debug(f"{engine.name} stopped")
                            except AttributeError:
                                pass
                    self.log.debug("Stop the black engine instances:")
                    self.log.debug("--------------------------------")
                    for engine in self.engines[chess.BLACK].values():
                        if engine is not None:
                            engine.quit()
                            try:
                                self.log.debug(f"{engine.name} stopped")
                            except AttributeError:
                                pass
                    self.log.debug("Stop the helper engine instance:")
                    self.log.debug("--------------------------------")
                    if self._helper_engine is not None:
                        self._helper_engine.quit()
                        try:
                            self.log.debug(f"{self._helper_engine.name} stopped")
                        except AttributeError:
                            pass
                    self.log.debug("Stop the reference engine instances:")
                    self.log.debug("------------------------------------")
                    for engine in self.engine_list:
                        if engine is not None:
                            engine.quit()
                            try:
                                self.log.debug(f"{engine.name} stopped")
                            except AttributeError:
                                pass
                    self.log.debug("The window is closing")
                    break
                else:
                    self.log.debug("Exit cancelled.")
                    self._init_popups(
                        event
                    )  # popup window re-initialized (to forget the result in a further call)

            elif event == Key.WHITE_TYPE:  # Select the white's type
                if values[Key.WHITE_TYPE] == Key.WHITE_HUMAN:
                    self._window[Key.BLACK_NET].update(disabled=False)
                    self._window[Key.START].update(disabled=False)
                    self.board_flipped = False  # board not flipped
                    if self.lan_finder.started and (values[Key.BLACK_TYPE] != Key.BLACK_NET):
                        self.lan_finder.shutdown()
                    self._players[chess.WHITE].type = Type.HUMAN
                    self._players[chess.WHITE].name = values[Key.WHITE_NAME]
                    if self.lan_finder.started:
                        self.lan_finder.local_player_name = self._players[chess.WHITE].name
                elif values[Key.WHITE_TYPE] == Key.WHITE_CPU:
                    self._window[Key.BLACK_NET].update(disabled=False)
                    if (
                        self._helper_engine is None
                    ):  # If no helper engine, then no engine at all
                        self._window[Key.START].update(disabled=True)
                    else:
                        self._window[Key.START].update(disabled=False)
                    if (
                        values[Key.BLACK_TYPE] == Key.BLACK_HUMAN
                    ):  # Flipped or not flipped ?
                        self.board_flipped = True
                    else:
                        self.board_flipped = False
                    if self.lan_finder.started and (values[Key.BLACK_TYPE] != Key.BLACK_NET):
                        self.lan_finder.shutdown()
                    self._players[chess.WHITE].type = Type.CPU
                    self._players[chess.WHITE].name = values[Key.WHITE_ENGINE_COMBO]
                    if self.lan_finder.started:
                        self.lan_finder.local_player_name = self._players[chess.WHITE].name
                elif values[Key.WHITE_TYPE] == Key.WHITE_NET:
                    self._window[Key.BLACK_NET].update(disabled=True) # Only one remote player at a time
                    self._window[Key.START].update(
                        disabled=True
                    )  # Network game not yet implemented
                    if (
                        values[Key.BLACK_TYPE] == Key.BLACK_HUMAN
                    ):  # Flipped or not flipped ?
                        self.board_flipped = True
                    else:
                        self.board_flipped = False
                    if self._window[Key.WHITE_NET_LAN_RADIO].get():
                        self.lan_finder.local_player_uuid = self._players[chess.BLACK].uuid
                        self.lan_finder.local_player_name = self._players[chess.BLACK].name
                        self.lan_finder.local_player_color = chess.BLACK
                        self.lan_finder.local_game_name = values[Key.CURRENT_GAME_NAME]
                        if not self.lan_finder.started:
                            self.lan_finder.start()
                        self._window.perform_long_operation(self._wait_for_new_remote_LAN_player, Key.NEW_REMOTE_PLAYER)
                        self._window.perform_long_operation(self._wait_for_change_remote_game_or_player_name, Key.CHANGE_OF_REMOTE_GAME_OR_PLAYER_NAME)
                        # self.lan_finder.local_game_uuid = ??? TBC
                    self._players[chess.WHITE].type = Type.NETWORK

            elif event == Key.BLACK_TYPE:  # Select the black's type
                if values[Key.BLACK_TYPE] == Key.BLACK_HUMAN:
                    self._window[Key.WHITE_NET].update(disabled=False)
                    self._window[Key.START].update(disabled=False)
                    if (
                        values[Key.WHITE_TYPE] == Key.WHITE_HUMAN
                    ):  # Flipped or not flipped ?
                        self.board_flipped = False
                    else:
                        self.board_flipped = True
                    if self.lan_finder.started and (values[Key.WHITE_TYPE] != Key.WHITE_NET):
                        self.lan_finder.shutdown()
                    self._players[chess.BLACK].type = Type.HUMAN
                    self._players[chess.BLACK].name = values[Key.BLACK_NAME]
                    if self.lan_finder.started:
                        self.lan_finder.local_player_name = self._players[chess.BLACK].name
                elif values[Key.BLACK_TYPE] == Key.BLACK_CPU:
                    self._window[Key.WHITE_NET].update(disabled=False)
                    if (
                        self._helper_engine is None
                    ):  # If no helper engine, then no engine at all
                        self._window[Key.START].update(disabled=True)
                    else:
                        self._window[Key.START].update(disabled=False)
                    self.board_flipped = False  # board not flipped
                    if self.lan_finder.started and (values[Key.WHITE_TYPE] != Key.WHITE_NET):
                        self.lan_finder.shutdown()
                    self._players[chess.BLACK].type = Type.CPU
                    self._players[chess.BLACK].name = values[Key.BLACK_ENGINE_COMBO]
                    if self.lan_finder.started:
                        self.lan_finder.local_player_name = self._players[chess.BLACK].name
                elif values[Key.BLACK_TYPE] == Key.BLACK_NET:
                    self._window[Key.WHITE_NET].update(disabled=True) # Only one remote player at a time
                    self._window[Key.START].update(
                        disabled=True
                    )  # Network game not yet implemented
                    self.board_flipped = False  # board not flipped
                    if self._window[Key.BLACK_NET_LAN_RADIO].get():
                        self.lan_finder.local_player_uuid = self._players[chess.WHITE].uuid
                        self.lan_finder.local_player_name = self._players[chess.WHITE].name
                        self.lan_finder.local_player_color = chess.WHITE
                        self.lan_finder.local_game_name = values[Key.CURRENT_GAME_NAME]
                        if not self.lan_finder.started:
                            self.lan_finder.start()
                        self._window.perform_long_operation(self._wait_for_new_remote_LAN_player, Key.NEW_REMOTE_PLAYER)
                        self._window.perform_long_operation(self._wait_for_change_remote_game_or_player_name, Key.CHANGE_OF_REMOTE_GAME_OR_PLAYER_NAME)
                        # self.lan_finder.local_game_uuid = ??? TBC
                    self._players[chess.BLACK].type = Type.NETWORK

            elif event == Key.CURRENT_GAME_NAME: # The name of the game has been changed
                 if self.lan_finder.started:
                    self.lan_finder.local_game_name = values[Key.CURRENT_GAME_NAME]
            
            elif event == Key.WHITE_NAME: # The name of the human, white player has been changed
                self._players[chess.WHITE].name = values[Key.WHITE_NAME]
                if self.lan_finder.started:
                    self.lan_finder.local_player_name = self._players[chess.WHITE].name
            
            elif event == Key.BLACK_NAME: # The name of the human, black player has been changed
                self._players[chess.BLACK].name = values[Key.BLACK_NAME]
                if self.lan_finder.started:
                    self.lan_finder.local_player_name = self._players[chess.BLACK].name
            
            elif (
                event == Key.WHITE_ENGINE_COMBO
            ):  # Change the engine for the CPU white player
                player = chess.WHITE
                engine_name = values[Key.WHITE_ENGINE_COMBO]
                self._update_cpu_tab(player, engine_name)
                self._players[chess.WHITE].name = engine_name
                if self.lan_finder.started:
                    self.lan_finder.local_player_name = self._players[chess.WHITE].name

            elif (
                event == Key.BLACK_ENGINE_COMBO
            ):  # Change the engine for the CPU black player
                player = chess.BLACK
                engine_name = values[Key.BLACK_ENGINE_COMBO]
                self._update_cpu_tab(player, engine_name)
                self._players[chess.BLACK].name = engine_name
                if self.lan_finder.started:
                    self.lan_finder.local_player_name = self._players[chess.BLACK].name

            elif (
                event == Key.WHITE_CPU_LEVEL_SLIDER
            ):  # Change the level for the CPU white player
                engine_name = values[Key.WHITE_ENGINE_COMBO]
                if "UCI_Elo" in self.engines[chess.WHITE][engine_name].engine_options:
                    if (
                        "UCI_LimitStrength"
                        in self.engines[chess.WHITE][engine_name].engine_options
                    ):
                        self.engine_options[chess.WHITE][
                            engine_name
                        ].UCI_LimitStrength = True
                    self.engine_options[chess.WHITE][engine_name].UCI_Elo = values[
                        Key.WHITE_CPU_LEVEL_SLIDER
                    ]

            elif (
                event == Key.BLACK_CPU_LEVEL_SLIDER
            ):  # Change the level for the CPU black player
                engine_name = values[Key.BLACK_ENGINE_COMBO]
                if "UCI_Elo" in self.engines[chess.BLACK][engine_name].engine_options:
                    if (
                        "UCI_LimitStrength"
                        in self.engines[chess.BLACK][engine_name].engine_options
                    ):
                        self.engine_options[chess.BLACK][
                            engine_name
                        ].UCI_LimitStrength = True
                    self.engine_options[chess.BLACK][engine_name].UCI_Elo = values[
                        Key.BLACK_CPU_LEVEL_SLIDER
                    ]

            elif event == Key.WHITE_NET_LAN_RADIO:  # The remote, white player is on the LAN
                self._window[Key.WHITE_NET_SERVER_TEXT].update(visible=False)
                self._window[Key.WHITE_NET_LAN_TABLE].update(visible=True)

            elif event == Key.WHITE_NET_SERVER_RADIO:  # The remote, white player is reachable through a server
                self._window[Key.WHITE_NET_SERVER_TEXT].update(visible=True)
                self._window[Key.WHITE_NET_LAN_TABLE].update(visible=False)

            elif event == Key.BLACK_NET_LAN_RADIO:  # The remote, black player is on the LAN
                self._window[Key.BLACK_NET_SERVER_TEXT].update(visible=False)
                self._window[Key.BLACK_NET_LAN_TABLE].update(visible=True)

            elif event == Key.BLACK_NET_SERVER_RADIO:  # The remote, black player is reachable through a server
                self._window[Key.BLACK_NET_SERVER_TEXT].update(visible=True)
                self._window[Key.BLACK_NET_LAN_TABLE].update(visible=False)

            elif event == Key.START:  # Start game
                self.log.debug("A new game is beginning...")
                self._window[Key.ABORD].update(visible=True, disabled=False)
                self._window[Key.START].update(disabled=True)
                sg.cprint("A new game is beginning !")
                sg.cprint("White player:", end=" ", t="black")
                if values[Key.WHITE_TYPE] == Key.WHITE_HUMAN:
                    white_name = values[Key.WHITE_NAME]
                    sg.cprint(f"{white_name}, local human.", t="black")
                    self.log.debug(f"White player: {white_name}, local human.")
                    self._window[Key.WHITE_NAME].update(disabled=True)
                    self._window[Key.WHITE_CPU].update(disabled=True)
                    self._window[Key.WHITE_NET].update(disabled=True)
                elif values[Key.WHITE_TYPE] == Key.WHITE_CPU:
                    white_name = values[Key.WHITE_ENGINE_COMBO]
                    sg.cprint(f"{white_name}, local CPU,", end=" ", t="black")
                    self.log.debug(f"White player: {white_name}, local CPU.")
                    if (
                        "UCI_Elo"
                        in self.engines[chess.WHITE][white_name].engine_options
                    ):
                        sg.cprint(
                            f"ELO = {self.engines[chess.WHITE][white_name].option.UCI_Elo()},",
                            end=" ",
                            t="black",
                        )
                        self.log.debug(
                            f"ELO = {self.engines[chess.WHITE][white_name].option.UCI_Elo()}"
                        )
                    self.engines[chess.WHITE][white_name].search_time = float(
                        values[Key.WHITE_CPU_DURATION]
                    )
                    sg.cprint(
                        f"turn duration = {self.engines[chess.WHITE][white_name].search_time} s.",
                        t="black",
                    )
                    self.log.debug(
                        f"Turn duration = {self.engines[chess.WHITE][white_name].search_time} s."
                    )
                    self._window[Key.WHITE_HUMAN].update(disabled=True)
                    self._window[Key.WHITE_CPU].update(disabled=False)
                    self._window[Key.WHITE_NET].update(disabled=True)
                elif values[Key.WHITE_TYPE] == Key.WHITE_NET:
                    white_name = "REMOTE"
                    sg.cprint(f"{white_name}, remote opponent.", t="black")
                    self.log.debug(f"White player: {white_name}, remote opponent.")
                    self._window[Key.WHITE_HUMAN].update(disabled=True)
                    self._window[Key.WHITE_CPU].update(disabled=True)
                    self._window[Key.WHITE_NET].update(disabled=False)
                else:
                    white_name = "UNKNOWN"
                    sg.cprint(f"{white_name}, unknown.", t="black")
                    self.log.debug(f"White player: {white_name}, unknown.")
                    self._window[Key.WHITE_HUMAN].update(disabled=True)
                    self._window[Key.WHITE_CPU].update(disabled=True)
                    self._window[Key.WHITE_NET].update(disabled=True)
                sg.cprint("Black player:", end=" ", c="white on black")
                if values[Key.BLACK_TYPE] == Key.BLACK_HUMAN:
                    black_name = values[Key.BLACK_NAME]
                    sg.cprint(f"{black_name}, local human.", c="white on black")
                    self.log.debug(f"Black player: {black_name}, local human.")
                    self._window[Key.BLACK_NAME].update(disabled=True)
                    self._window[Key.BLACK_CPU].update(disabled=True)
                    self._window[Key.BLACK_NET].update(disabled=True)
                elif values[Key.BLACK_TYPE] == Key.BLACK_CPU:
                    black_name = values[Key.BLACK_ENGINE_COMBO]
                    sg.cprint(f"{black_name}, local CPU.", end=" ", c="white on black")
                    self.log.debug(f"Black player: {black_name}, local CPU.")
                    if (
                        "UCI_Elo"
                        in self.engines[chess.BLACK][black_name].engine_options
                    ):
                        sg.cprint(
                            f"ELO = {self.engines[chess.BLACK][black_name].option.UCI_Elo()},",
                            end=" ",
                            c="white on black",
                        )
                        self.log.debug(
                            f"ELO = {self.engines[chess.BLACK][black_name].option.UCI_Elo()}"
                        )
                    self.engines[chess.BLACK][black_name].search_time = float(
                        values[Key.BLACK_CPU_DURATION]
                    )
                    sg.cprint(
                        f"turn duration = {self.engines[chess.BLACK][black_name].search_time} s.",
                        c="white on black",
                    )
                    self.log.debug(
                        f"Turn duration = {self.engines[chess.BLACK][black_name].search_time} s."
                    )
                    self._window[Key.BLACK_HUMAN].update(disabled=True)
                    self._window[Key.BLACK_CPU].update(disabled=False)
                    self._window[Key.BLACK_NET].update(disabled=True)
                elif values[Key.BLACK_TYPE] == Key.BLACK_NET:
                    black_name = "REMOTE"
                    sg.cprint(f"{black_name}, remote opponent.", c="white on black")
                    self.log.debug(f"Black player: {black_name}, remote opponent.")
                    self._window[Key.BLACK_HUMAN].update(disabled=True)
                    self._window[Key.BLACK_CPU].update(disabled=True)
                    self._window[Key.BLACK_NET].update(disabled=False)
                else:
                    black_name = "UNKNOWN"
                    sg.cprint(f"{black_name}, unknown.", c="white on black")
                    self.log.debug(f"Black player: {black_name}, unknown.")
                    self._window[Key.BLACK_HUMAN].update(disabled=True)
                    self._window[Key.BLACK_CPU].update(disabled=True)
                    self._window[Key.BLACK_NET].update(disabled=True)

                self._window[Key.CURRENT_GAME_NAME].update(disabled=True)

                self._game = self._prepare_game(
                    white_name=white_name,
                    white_type=values[Key.WHITE_TYPE],
                    black_name=black_name,
                    black_type=values[Key.BLACK_TYPE],
                    values=values,
                )
                self._game.ongoing = True

                self._window[Key.CURRENT_PLAYER_NAME].update(
                    self._game.players[chess.WHITE].name
                )
                self._window[Key.CURRENT_PLAYER_IMAGE].update(
                    self._current_white_png_bytes
                )

                if self._helper_engine is not None:
                    if self._game.players[chess.WHITE].type == Type.HUMAN:
                        self._window[Key.HELP].update(visible=True, disabled=False)
                    else:
                        self._window[Key.HELP].update(visible=False, disabled=True)
                else:
                    self._window[Key.HELP].update(visible=False, disabled=True)

                self._start_pos = None  # Starting position of a move
                self._dest_pos = None  # Ending position of a move

                if (
                    values[Key.WHITE_TYPE] == Key.WHITE_CPU
                ):  # If the white player is an engine, start it
                    self._white_engine = self.engines[chess.WHITE][white_name]
                    self._white_engine.start_new_game(values[Key.CURRENT_GAME_NAME])
                    self._window.perform_long_operation(
                        lambda: self._white_engine.next_move(self._game.board),
                        Key.CPU_OR_REMOTE_MOVE,
                    )
                if values[Key.BLACK_TYPE] == Key.BLACK_CPU:
                    self._black_engine = self.engines[chess.BLACK][black_name]
                    self._black_engine.start_new_game(values[Key.CURRENT_GAME_NAME])

            elif event == Key.ABORD:  # Abord game
                if self._confirm_abord_popup.read(close=True)[0] == Key.YES:
                    self.log.debug("Game aborded")
                    self._game.ongoing = False
                    self._init_before_start()
                    sg.cprint("Game aborded.")
                else:
                    self.log.debug("Abord cancelled")
                self._init_popups(
                    event
                )  # popup window re-initialized (to forget the result in a further call)

            elif event == Key.HELP:  # Ask for help
                self.log.debug(
                    f"{self._game.players[self._game.current_color].name} asks for help."
                )
                self._window.perform_long_operation(
                    self._game.ask_for_help, Key.REPLY_TO_HELP
                )
                self._window[Key.HELP].update(disabled=True)

            elif event == Key.CLAIM:  # Claim for a draw
                if self._draw_claimed == Draw.THREEFOLD:
                    key_popup = KeyPopup.DRAW
                    params = {
                        "draw": Draw.THREEFOLD,
                        "player": self._game.players[self._game.current_color].name,
                    }
                elif self._draw_claimed == Draw.FIFTY:
                    key_popup = KeyPopup.DRAW
                    params = {
                        "draw": Draw.FIFTY,
                        "player": self._game.players[self._game.current_color].name,
                    }
                self._dyn_popup(key_popup, params)
                self.log.debug("Game finished")
                self._game.ongoing = False
                self._init_before_start()
                sg.cprint("Game finished.")

            elif event == Key.BOARD + "_left_click":  # Start or finish a move
                if (
                    hasattr(self, "_game") and self._game.ongoing
                ):  # Only if a game is ongoing
                    user_event = self._window[Key.BOARD].user_bind_event
                    square = self._coord_to_square((user_event.x, user_event.y))
                    self.log.debug(
                        f"Left click at ({user_event.x},{user_event.y}): square {chess.square_name(square) if square is not None else None}"
                    )

                    if (
                        self.board.color_at(square) is not None
                        and (self.board.color_at(square) == self._game.current_color)
                        and (
                            self._game.players[self._game.current_color].type
                            == Type.HUMAN
                        )
                    ):
                        if self._start_pos is None:
                            self._reachable_squares = (
                                self._game.reaching_squares_from_pos(square)
                            )
                            self.log.debug(
                                f"Reachable squares: {tuple(chess.square_name(reachable) for reachable in self._reachable_squares)}"
                            )
                            if len(self._reachable_squares) > 0:
                                fill = {
                                    square: BoardColor.START_SQUARE
                                } | dict.fromkeys(
                                    self._reachable_squares, BoardColor.REACHABLE_SQUARE
                                )
                                board_svg_str = chess.svg.board(
                                    self.board,
                                    fill=fill,
                                    size=self._board_size,
                                    flipped=self.board_flipped,
                                )
                                png_bytes = self.svg_to_png_bytes(board_svg_str)
                                self._window[Key.BOARD].update(source=png_bytes)
                                self._start_pos = square
                        elif square == self._start_pos:
                            board_svg_str = chess.svg.board(
                                self.board,
                                size=self._board_size,
                                flipped=self.board_flipped,
                            )
                            png_bytes = self.svg_to_png_bytes(board_svg_str)
                            self._window[Key.BOARD].update(source=png_bytes)
                            self._start_pos = None
                    elif square in self._reachable_squares:
                        self.log.debug(
                            f"Destination chosen: {chess.square_name(square)}"
                        )
                        self._dest_pos = square
                        if self._game.current_color == chess.WHITE:
                            sg.cprint(f"{self._game.current_turn}.", end=" ")
                        # Test for promotion
                        if self.board.piece_type_at(self._start_pos) == chess.PAWN:
                            if (
                                self._game.current_color == chess.WHITE
                                and chess.square_rank(square) == 7
                            ) or (
                                self._game.current_color == chess.BLACK
                                and chess.square_rank(square) == 0
                            ):
                                promotion_key, _ = self._dyn_popup(
                                    key_popup=KeyPopup.PROMOTION,
                                    params={"player": self._game.current_color},
                                )
                                if promotion_key == Key.ROOK:
                                    promotion = chess.ROOK
                                elif promotion_key == Key.KNIGHT:
                                    promotion = chess.KNIGHT
                                elif promotion_key == Key.BISHOP:
                                    promotion = chess.BISHOP
                                else:
                                    promotion = chess.QUEEN
                            else:
                                promotion = None
                        else:
                            promotion = None

                        result = self._game.add_move(
                            chess.Move(
                                from_square=self._start_pos,
                                to_square=self._dest_pos,
                                promotion=promotion,
                            )
                        )
                        sg.cprint(f"{result.san}", end=" ")
                        self.board = self._game.current_board

                        if (
                            game_result := self._game.result_with_claim
                        ):  # the game has ended with a chessmate or a draw without a claim, or a draw can be claimed
                            self.log.debug(
                                f"The game terminates (or a draw is claimable) on the following result code: {game_result.termination}"
                            )
                            if game_result.termination == chess.Termination.CHECKMATE:
                                self.log.info(
                                    f"Chessmate ! The {'white' if game_result.winner else 'black'} player {self._game.players[game_result.winner].name} wins the game."
                                )
                                key_popup = KeyPopup.CHESSMATE
                                params = {
                                    "winner": game_result.winner,
                                    "name_winner": self._game.players[
                                        game_result.winner
                                    ].name,
                                }
                                game_is_finished = True
                            elif game_result.termination == chess.Termination.STALEMATE:
                                self.log.info(
                                    f"Stalemate: {'white' if self._game.current_color else 'black'} player has no possible legal move ! No winner."
                                )
                                key_popup = KeyPopup.DRAW
                                params = {
                                    "draw": Draw.STALEMATE,
                                    "player": self._game.players[
                                        self._game.current_color
                                    ].name,
                                }
                                game_is_finished = True
                            elif (
                                game_result.termination
                                == chess.Termination.INSUFFICIENT_MATERIAL
                            ):
                                self.log.info(
                                    f"{'White' if self._game.current_color else 'Black'} player has no sufficient material to win ! No winner."
                                )
                                key_popup = KeyPopup.DRAW
                                params = {
                                    "draw": Draw.INSUFFICIENT_MATERIAL,
                                    "player": self._game.players[
                                        self._game.current_color
                                    ].name,
                                }
                                game_is_finished = True
                            elif (
                                game_result.termination
                                == chess.Termination.SEVENTYFIVE_MOVES
                            ):
                                self.log.info(
                                    "No capture or no pawn move has occured in the last 75 moves ! No winner."
                                )
                                key_popup = KeyPopup.DRAW
                                params = {"draw": Draw.SEVENTY_FIVE}
                                game_is_finished = True
                            elif (
                                game_result.termination
                                == chess.Termination.FIVEFOLD_REPETITION
                            ):
                                self.log.info(
                                    "An identical position occurs five times ! No winner."
                                )
                                key_popup = KeyPopup.DRAW
                                params = {"draw": Draw.FIVEFOLD}
                                game_is_finished = True
                            elif (
                                game_result.termination == chess.Termination.FIFTY_MOVES
                            ):
                                key_popup = None  # The popup window will be called later, if the draw is claimed
                                self._draw_claimed = Draw.FIFTY
                                self._window[Key.CLAIM].update(
                                    text=Text.CLAIM_FOR_FIFTY,
                                    visible=True,
                                    disabled=False,
                                )
                                game_is_finished = False
                            elif (
                                game_result.termination
                                == chess.Termination.THREEFOLD_REPETITION
                            ):
                                key_popup = None  # The popup window will be called later, if the draw is claimed
                                self._draw_claimed = Draw.THREEFOLD
                                self._window[Key.CLAIM].update(
                                    text=Text.CLAIM_FOR_THREEFOLD,
                                    visible=True,
                                    disabled=False,
                                )
                                game_is_finished = False
                            else:
                                key_popup = None
                                game_is_finished = False
                            if key_popup:
                                self._dyn_popup(key_popup, params)

                            if game_is_finished:  # Game is finished: re-init the board
                                self.log.debug("Game finished")
                                self._game.ongoing = False
                                self._init_before_start()
                                sg.cprint("Game finished.")
                            else:
                                self._window[Key.CURRENT_PLAYER_NAME].update(
                                    self._game.players[self._game.current_color].name
                                )
                                self._window[Key.CURRENT_PLAYER_IMAGE].update(
                                    self._current_white_png_bytes
                                    if self._game.current_color
                                    else self._current_black_png_bytes
                                )
                        else:
                            self._window[Key.CURRENT_PLAYER_NAME].update(
                                self._game.players[self._game.current_color].name
                            )
                            self._window[Key.CURRENT_PLAYER_IMAGE].update(
                                self._current_white_png_bytes
                                if self._game.current_color
                                else self._current_black_png_bytes
                            )
                            if self._helper_engine is not None:
                                if (
                                    self._game.players[self._game.current_color].type
                                    == Type.HUMAN
                                ):
                                    self._window[Key.HELP].update(
                                        visible=True, disabled=False
                                    )
                                else:
                                    self._window[Key.HELP].update(
                                        visible=False, disabled=True
                                    )
                            else:
                                self._window[Key.HELP].update(
                                    visible=False, disabled=True
                                )
                            self._window[Key.CLAIM].update(visible=False, disabled=True)

                        self._start_pos = None
                        self._dest_pos = None

                        if (
                            self._game.players[self._game.current_color].type
                            == Type.CPU
                            and self._game.ongoing
                        ):
                            if self._game.current_color == chess.WHITE:
                                try:
                                    self._window.perform_long_operation(
                                        lambda: self._white_engine.next_move(
                                            self.board
                                        ),
                                        Key.CPU_OR_REMOTE_MOVE,
                                    )
                                except chess.engine.EngineTerminatedError:  # The engine is already closed (if the game is aborded for instance)
                                    self.log.debug(
                                        "White engine attempts to make a move but the game is already finished."
                                    )
                            else:
                                try:
                                    self._window.perform_long_operation(
                                        lambda: self._black_engine.next_move(
                                            self.board
                                        ),
                                        Key.CPU_OR_REMOTE_MOVE,
                                    )
                                except chess.engine.EngineTerminatedError:  # The engine is already closed (if the game is aborded for instance)
                                    self.log.debug(
                                        "Black engine attempts to make a move but the game is already finished."
                                    )

            elif (
                event == Key.REPLY_TO_HELP
            ):  # Reception of the reply for asking to help
                if values[event]:
                    self.log.debug(
                        f"The best move according to the helper engine is: from {chess.square_name(values[event].from_square)} to {chess.square_name(values[event].to_square)}"
                    )
                    arrows = [
                        chess.svg.Arrow(
                            values[event].from_square,
                            values[event].to_square,
                            color=BoardColor.ARROW,
                        )
                    ]
                    board_svg_str = chess.svg.board(
                        self.board,
                        arrows=arrows,
                        size=self._board_size,
                        flipped=self.board_flipped,
                    )
                    png_bytes = self.svg_to_png_bytes(board_svg_str)
                    self._window[Key.BOARD].update(source=png_bytes)
                self._window[Key.HELP].update(disabled=False)

            elif (
                event == Key.CPU_OR_REMOTE_MOVE
            ):  # Receipt of the move of the local engine or a remote opponent
                if (
                    not self._game.ongoing
                ):  # If the has been aborded during the previous analysis
                    if self._game.players[chess.WHITE].type == Type.CPU:
                        self._white_engine.quit()
                    if self._game.players[chess.BLACK].type == Type.CPU:
                        self._black_engine.quit()
                elif values[event]:
                    self.log.debug(
                        f"Engine or remote opponent move: from {chess.square_name(values[event].from_square)} to {chess.square_name(values[event].to_square)}"
                    )
                    result = self._game.add_move(values[event])
                    sg.cprint(f"{result.san}", end=" ")
                    self.board = self._game.current_board

                    if (
                        game_result := self._game.result_with_claim
                    ):  # the game has ended with a chessmate or a draw without a claim, or a draw can be claimed
                        self.log.debug(
                            f"The game terminates (or a draw is claimable) on the following result code: {game_result.termination}"
                        )
                        if game_result.termination == chess.Termination.CHECKMATE:
                            self.log.info(
                                f"Chessmate ! The {'white' if game_result.winner else 'black'} player {self._game.players[game_result.winner].name} wins the game."
                            )
                            key_popup = KeyPopup.CHESSMATE
                            params = {
                                "winner": game_result.winner,
                                "name_winner": self._game.players[
                                    game_result.winner
                                ].name,
                            }
                            game_is_finished = True
                        elif game_result.termination == chess.Termination.STALEMATE:
                            self.log.info(
                                f"Stalemate: {'white' if self._game.current_color else 'black'} player has no possible legal move ! No winner."
                            )
                            key_popup = KeyPopup.DRAW
                            params = {
                                "draw": Draw.STALEMATE,
                                "player": self._game.players[
                                    self._game.current_color
                                ].name,
                            }
                            game_is_finished = True
                        elif (
                            game_result.termination
                            == chess.Termination.INSUFFICIENT_MATERIAL
                        ):
                            self.log.info(
                                f"{'White' if self._game.current_color else 'Black'} player has no sufficient material to win ! No winner."
                            )
                            key_popup = KeyPopup.DRAW
                            params = {
                                "draw": Draw.INSUFFICIENT_MATERIAL,
                                "player": self._game.players[
                                    self._game.current_color
                                ].name,
                            }
                            game_is_finished = True
                        elif (
                            game_result.termination
                            == chess.Termination.SEVENTYFIVE_MOVES
                        ):
                            self.log.info(
                                "No capture or no pawn move has occured in the last 75 moves ! No winner."
                            )
                            key_popup = KeyPopup.DRAW
                            params = {"draw": Draw.SEVENTY_FIVE}
                            game_is_finished = True
                        elif (
                            game_result.termination
                            == chess.Termination.FIVEFOLD_REPETITION
                        ):
                            self.log.info(
                                "An identical position occurs five times ! No winner."
                            )
                            key_popup = KeyPopup.DRAW
                            params = {"draw": Draw.FIVEFOLD}
                            game_is_finished = True
                        elif game_result.termination == chess.Termination.FIFTY_MOVES:
                            key_popup = None  # The popup window will be called later, if the draw is claimed
                            self._draw_claimed = Draw.FIFTY
                            self._window[Key.CLAIM].update(
                                text=Text.CLAIM_FOR_FIFTY, visible=True, disabled=False
                            )
                            game_is_finished = False
                        elif (
                            game_result.termination
                            == chess.Termination.THREEFOLD_REPETITION
                        ):
                            key_popup = None  # The popup window will be called later, if the draw is claimed
                            self._draw_claimed = Draw.THREEFOLD
                            self._window[Key.CLAIM].update(
                                text=Text.CLAIM_FOR_THREEFOLD,
                                visible=True,
                                disabled=False,
                            )
                            game_is_finished = False
                        else:
                            key_popup = None
                            game_is_finished = False
                        if key_popup:
                            self._dyn_popup(key_popup, params)

                        if game_is_finished:  # Game is finished: re-init the board
                            self.log.debug("Game finished")
                            self._game.ongoing = False
                            self._init_before_start()
                            sg.cprint("Game finished.")
                        else:
                            self._window[Key.CURRENT_PLAYER_NAME].update(
                                self._game.players[self._game.current_color].name
                            )
                            self._window[Key.CURRENT_PLAYER_IMAGE].update(
                                self._current_white_png_bytes
                                if self._game.current_color
                                else self._current_black_png_bytes
                            )
                    else:
                        self._window[Key.CURRENT_PLAYER_NAME].update(
                            self._game.players[self._game.current_color].name
                        )
                        self._window[Key.CURRENT_PLAYER_IMAGE].update(
                            self._current_white_png_bytes
                            if self._game.current_color
                            else self._current_black_png_bytes
                        )
                        if self._helper_engine is not None:
                            if (
                                self._game.players[self._game.current_color].type
                                == Type.HUMAN
                            ):
                                self._window[Key.HELP].update(
                                    visible=True, disabled=False
                                )
                            else:
                                self._window[Key.HELP].update(
                                    visible=False, disabled=True
                                )
                        else:
                            self._window[Key.HELP].update(visible=False, disabled=True)
                        self._window[Key.CLAIM].update(visible=False, disabled=True)

                    self._start_pos = None
                    self._dest_pos = None

                    if (
                        self._game.players[self._game.current_color].type == Type.CPU
                        and self._game.ongoing
                    ):
                        if self._game.current_color == chess.WHITE:
                            self._window.perform_long_operation(
                                lambda: self._white_engine.next_move(self.board),
                                Key.CPU_OR_REMOTE_MOVE,
                            )
                        else:
                            self._window.perform_long_operation(
                                lambda: self._black_engine.next_move(self.board),
                                Key.CPU_OR_REMOTE_MOVE,
                            )
            
            elif event == Key.NEW_REMOTE_PLAYER: # A new remote player is available
                if self.lan_finder.started:
                    # if (values[Key.WHITE_TYPE] == Key.WHITE_NET) and self._window[Key.WHITE_NET_LAN_RADIO].get():
                        # self.lan_finder.send_player_characteristics(self._players[chess.BLACK])
                    # elif (values[Key.BLACK_TYPE] == Key.BLACK_NET) and self._window[Key.BLACK_NET_LAN_RADIO].get():
                        # self.lan_finder.send_player_characteristics(self._players[chess.WHITE])
                    # else:
                        # pass
                    
                    # self.lan_finder.send_game_charact(charact=opcode.GAMENAME, value=values[Key.CURRENT_GAME_NAME])

                    self._window.perform_long_operation(self._wait_for_new_remote_LAN_player, Key.NEW_REMOTE_PLAYER)
            
            elif event == Key.CHANGE_OF_REMOTE_GAME_OR_PLAYER_NAME: # The name of a remote game or player has changed
                if self.lan_finder.started:
                    self._update_lan_table(values[event])
                    self._window.perform_long_operation(self._wait_for_change_remote_game_or_player_name, Key.CHANGE_OF_REMOTE_GAME_OR_PLAYER_NAME)
            
        
        # Close window
        self._window.close()


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
