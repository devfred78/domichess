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
	Module network: network management
"""


# Standard modules
# -----------------
from enum import Enum, StrEnum, IntEnum, auto
import errno
import ipaddress
import json
import logging
import os
import socket
from socketserver import ThreadingUDPServer, ThreadingTCPServer, DatagramRequestHandler, StreamRequestHandler
import struct
import sys
import threading
import time
from uuid import uuid4

# Third party modules
# --------------------
import chess
import netifaces

# Internal modules
# -----------------
from domichess import Type, Draw
from domichess.game import Player, Game

# namedtuples
# ------------

# Enumerations
# -------------
class opcode(IntEnum):  # operations for network transactions
    IAMHERE = auto()  # Declaration of a new player
    KEEPALIVE = auto()  # The player is still available
    PLAYERNAME = auto()  # The name of the player
    PLAYERUUID = auto()  # UUID of the player
    PLAYERCOLOR = auto()  # Color of the player
    PLAYERFULL = auto()  # All characteristics of the player
    GAMENAME = auto()  # The name of the game hosted by the server
    GAMEUUID = auto()  # UUID of the game
    GAMEFULL = auto()  # The name and the UUID of a game
    GAMEJOIN = auto()  # Join the remote game
    GAMELEAVE = auto()  # Leave the remote game
    GAMESTART = auto()  # The local game is about to start
    GAMEDELETE = auto() # Delete a game
    WITHDRAWAL = auto()  # Abord the current game
    MOVE = auto()   # A chess move
    CLAIM = auto()  # A claim for a draw
    QUIT = auto()  # Quit the network
    UNREACHABLE = auto()  # The opponent is unreachable
    SUCCESSFUL = auto()  # Action successfully completed
    UNSUCCESSFUL = auto()  # Action not performed correctly


# Global constants
# -----------------


# Dataclasses
# ------------

# Classes
# --------


class FinderHandler(DatagramRequestHandler):
    """
    Handler instanciated in response to a request to the finder server.
    """

    def handle(self):
        """
        Analyses a message sent by a client.

        Depending on the received opcode, records, updates or erases the remote players (or part of characteristics of).
        """

        # Discard messages from the local player
        if self.client_address[0] != self.server.local_address:
            data = self.request[0]
            recv_opcode = data[0]
            if recv_opcode == opcode.IAMHERE:
                self.server.log.debug(
                    f"Receipt of a declaration of a new player from {self.client_address[0]}"
                )
                if self.client_address[0] not in self.server.play_addr:
                    self.server.log.info(
                        f"{self.client_address[0]} added to the list of the remote players"
                    )
                    with self.server.addr_lock:
                        self.server.play_addr.append(self.client_address[0])
                    self.server.log.debug(
                        f"Reply to {self.client_address[0]}: declared as a new player"
                    )
                    # Reply to the remote server and not the client since the latter has not been listening to anymore
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.sendto(
                        bytes([opcode.IAMHERE]),
                        (self.client_address[0], self.server.port),
                    )
                else:
                    self.server.log.debug(
                        f"{self.client_address[0]} is already known as an available player"
                    )
            elif recv_opcode == opcode.KEEPALIVE:
                self.server.log.debug(
                    f"Receipt of a keep alive from {self.client_address[0]}"
                )
                # In case of the first broadcast message was not received
                if self.client_address[0] not in self.server.play_addr:
                    self.server.log.info(
                        f"{self.client_address[0]} added to the list of the remote players"
                    )
                    with self.server.addr_lock:
                        self.server.play_addr.append(self.client_address[0])
                self.server.log.debug(f"Reply to {self.client_address[0]}: keep alive")
                self.request[1].sendto(bytes([opcode.KEEPALIVE]), self.client_address)
            elif recv_opcode == opcode.PLAYERNAME:
                name = json.loads(str(data[1:], "utf-8"))
                self.server.log.info(
                    f"Name of the player {self.client_address[0]} is: {name}"
                )
                if self.client_address[0] in self.server.remote_players:
                    self.server.log.debug(
                        f"the name of the player {self.client_address[0]} is updated"
                    )
                    with self.server.players_lock:
                        self.server.remote_players[self.client_address[0]].name = name
                else:
                    player = Player(name=name, type=Type.NETWORK)
                    self.server.log.debug(
                        f"The player {self.client_address[0]} is created"
                    )
                    with self.server.players_lock:
                        self.server.remote_players[self.client_address[0]] = player
            elif recv_opcode == opcode.PLAYERUUID:
                uuid = json.loads(str(data[1:], "utf-8"))
                self.server.log.info(
                    f"UUID of the player {self.client_address[0]} is: {uuid}"
                )
                if self.client_address[0] in self.server.remote_players:
                    player = self.server.remote_players[self.client_address[0]]
                    if player.uuid == uuid:
                        self.server.log.debug(
                            f"The player {self.client_address[0]} is already registred with this UUID"
                        )
                    else:
                        player = Player(type=Type.NETWORK, uuid=uuid)
                        self.server.log.debug(
                            f"The player {self.client_address[0]} is re-created with a new UUID"
                        )
                        with self.server.players_lock:
                            self.server.remote_players[self.client_address[0]] = player
                else:
                    player = Player(type=Type.NETWORK, uuid=uuid)
                    self.server.log.debug(
                        f"The player {self.client_address[0]} is created"
                    )
                    with self.server.players_lock:
                        self.server.remote_players[self.client_address[0]] = player
            elif recv_opcode == opcode.PLAYERCOLOR:
                color = json.loads(str(data[1:], "utf-8"))
                self.server.log.info(
                    f"Color of the player {self.client_address[0]} is: {'WHITE' if color else 'BLACK'}"
                )
                if self.client_address[0] in self.server.remote_players:
                    self.server.log.debug(
                        f"the color of the player {self.client_address[0]} is updated"
                    )
                    with self.server.players_lock:
                        self.server.remote_players[self.client_address[0]].color = color
                else:
                    player = Player(color=color, type=Type.NETWORK)
                    self.server.log.debug(
                        f"The player {self.client_address[0]} is created"
                    )
                    with self.server.players_lock:
                        self.server.remote_players[self.client_address[0]] = player
            elif recv_opcode == opcode.PLAYERFULL:
                player_full = json.loads(str(data[1:], "utf-8"))
                self.server.log.info(
                    f"The characteristics of the player {self.client_address[0]} are:\n    UUID: {player_full['uuid']}\n    Name: {player_full['name']}\n    Color: {'WHITE' if player_full['color'] else 'BLACK'}"
                )
                player = Player(
                    name=player_full["name"],
                    color=player_full["color"],
                    type=Type.NETWORK,
                    uuid=player_full["uuid"],
                )
                with self.server.players_lock:
                    self.server.remote_players[self.client_address[0]] = player
            elif recv_opcode == opcode.GAMENAME:
                game_name = json.loads(str(data[1:], "utf-8"))
                self.server.log.info(
                    f"Name of the game hosted by {self.client_address[0]} is: {game_name}"
                )
                if self.client_address[0] in self.server.remote_games:
                    self.server.log.debug(
                        f"The name of the game hosted by {self.client_address[0]} is updated"
                    )
                    with self.server.games_lock:
                        self.server.remote_games[self.client_address[0]][
                            "name"
                        ] = game_name
                else:
                    game = {"name": game_name, "uuid": str(uuid4())}
                    self.server.log.debug(
                        f"The game hosted by {self.client_address[0]} is created"
                    )
                    with self.server.players_lock:
                        self.server.remote_games[self.client_address[0]] = game
            elif recv_opcode == opcode.GAMEUUID:
                game_uuid = json.loads(str(data[1:], "utf-8"))
                self.server.log.info(
                    f"UUID of the game hosted by {self.client_address[0]} is: {game_uuid}"
                )
                if self.client_address[0] in self.server.remote_games:
                    self.server.log.debug(
                        f"The UUID of the game hosted by {self.client_address[0]} is updated"
                    )
                    with self.server.games_lock:
                        self.server.remote_games[self.client_address[0]][
                            "uuid"
                        ] = game_uuid
                else:
                    game = {"name": "default", "uuid": game_uuid}
                    self.server.log.debug(
                        f"The game hosted by {self.client_address[0]} is created"
                    )
                    with self.server.players_lock:
                        self.server.remote_games[self.client_address[0]] = game
            elif recv_opcode == opcode.GAMEJOIN:
                self.server.log.info(
                    f"Player {self.client_address[0]} wants to join the local game"
                )
                with self.server.joined_lock:
                    self.server.joined_players[self.client_address[0]] = True
            elif recv_opcode == opcode.GAMELEAVE:
                self.server.log.info(
                    f"Player {self.client_address[0]} wants to leave the local game"
                )
                if self.client_address[0] in self.server.joined_players:
                    with self.server.joined_lock:
                        self.server.joined_players[self.client_address[0]] = False
            elif recv_opcode == opcode.GAMESTART:
                pass
            elif recv_opcode == opcode.QUIT:
                self.server.log.info(
                    f"The player {self.client_address[0]} is leaving the network"
                )
                if self.client_address[0] in self.server.play_addr:
                    with self.server.addr_lock:
                        self.server.play_addr.remove(self.client_address[0])
                if self.client_address[0] in self.server.remote_players:
                    with self.server.players_lock:
                        del self.server.remote_players[self.client_address[0]]
                if self.client_address[0] in self.server.remote_games:
                    with self.server.games_lock:
                        del self.server.remote_games[self.client_address[0]]
                if self.client_address[0] in self.server.joined_players:
                    with self.server.joined_lock:
                        del self.server.joined_players[self.client_address[0]]
            else:
                self.server.log.debug("Receipt of an unknown message")


class LANFinderServer(ThreadingUDPServer):
    """
    This class implements a server for finding other players on the LAN. It inherits the [socketserver.ThreadingUDPServer class](https://docs.python.org/3/library/socketserver.html?highlight=socket#socketserver.ThreadingUDPServer).

    This server waits for an UDP message on the given port, on all IP interfaces. In the same time, it sends an UDP call on the broadcast addresses of all IP interfaces, in order to attempt to reach other same servers in the LAN.

    Parameters:
            port:
                    The port number on which the server is listening to.
            server_port:
                    If you want to specify a distinct port for the current server. Mainly for test or investigation purposes. In most cases leave it unmodified.
            logger:
                    The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.

    Attributes:
            local_address:
                    IPv4 address of the local host. **read-only**
            port:
                    The port number on which the server is listening to. **read-only**
            broad_addr:
                    List of string representations of the broadcast addresses, using the IPv4 form (like `100.50.200.5`). **read-only** (but mutable)
            play_addr:
                    list of the IPv4 addresses of the available remote players on the LAN. **read-only** (but mutable)
            remote_games:
                    dictionnary of all remote games, keyed by IP addresses. Each value is a dictionnary {"name": name_of_the_game, "uuid": UUID_of_the_game}. **read-only** (but mutable)
            remote_players:
                    dictionnary of all connected remote players, keyed by IP addresses. Each value is a domichess.game.Player object. **read-only** (but mutable)
            joined_players:
                    dictionnary of all remote players wishing to join the local game, keyed by IP addresses. Each value is a boolean. **read-only** (but mutable)
            started:
                    `True` if the server is running. `False` otherwise. **read-only**
            log (logging.Logger):
                    Logger used to track events that append when the instance is running. Child of the `logger` provided, or a fake logger with a null handler. **read-only**
    """

    def __init__(
        self,
        port: int,
        server_port: int | None = None,
        logger: logging.Logger | None = None,
    ):

        if logger is None:
            self._log = logging.getLogger("LANFinderServer")
            self._log.addHandler(logging.NullHandler())
        else:
            self._log = logger.getChild("LANFinderServer")

        self._log.debug("--- LAN Finder Server initialization ---")

        if server_port is None:
            ser_port = port
        else:
            ser_port = server_port

        super().__init__(
            ("", ser_port), RequestHandlerClass=FinderHandler, bind_and_activate=True
        )

        self._started = False

        self._port = port

        # Find the IPv4 address of the local host
        host = socket.gethostname()
        self._local_address = socket.gethostbyname(host)

        # Find the broadcast addresses
        self._broad_addr = list()
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addresses = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addresses.keys():
                for cnx in addresses[netifaces.AF_INET]:
                    if (cnx["addr"] != "127.0.0.1") and ("broadcast" in cnx):
                        self._broad_addr.append(cnx["broadcast"])

        self._log.debug(f"Broadcasts addresses found: {self._broad_addr}")

        self._play_addr = list()
        self.addr_lock = threading.Lock()

        self._remote_players = dict()
        self.players_lock = threading.Lock()

        self._joined_players = dict()
        self.joined_lock = threading.Lock()

        self._remote_games = dict()
        self.games_lock = threading.Lock()

    @property
    def started(self) -> bool:
        # `True` if the server is running. `False` otherwise.
        return self._started

    @property
    def joined_players(self) -> dict:
        # dictionnary of all remote players wishing to join the local game, keyed by IP addresses
        return self._joined_players

    @property
    def remote_players(self) -> dict:
        # dictionnary of all connected remote players, keyed by IP addresses
        return self._remote_players

    @property
    def remote_games(self) -> dict:
        # dictionnary of all remote games, keyed by IP addresses
        return self._remote_games

    @property
    def local_address(self) -> str:
        # IPv4 address of the local host
        return self._local_address

    @property
    def port(self) -> int:
        # The port number on which the server is listening to.
        return self._port

    @property
    def play_addr(self) -> list:
        # list of the IPv4 addresses of the available remote players on the LAN.
        return self._play_addr

    @property
    def broad_addr(self) -> list:
        # List of string representations of the broadcast addresses, using the IPv4 form (like `100.50.200.5`)
        return self._broad_addr

    @property
    def log(self) -> logging.Logger:
        # Logger used to track events that append when the instance is running. Child of the `logger` provided, or a fake logger with a null handler.
        return self._log

    def start(self, blocking: bool = False):
        """
        Starts the server and seeks other players on the LAN.

        If `blocking`is False (the default), the server is executed in a separated thread - and then the method returns immediately. If True, the function blocks until the method `shutdown()` is called in a different thread.

        Parameters:
                blocking:
                        indicates whether the method blocks (True) or returns immediately (False)
        """

        if blocking:
            self.find_remote_players()
            self._log.info("Server activated in blocking mode. Stop it with CTRL-C.")
            self._log.info(f"Server listening at port {self.port}")
            self._started = True
            self.serve_forever()
        else:
            self._log.info("Server activated in non-blocking mode.")
            self._log.info(f"Server listening at port {self.port}")
            server_thread = threading.Thread(target=self.serve_forever)
            server_thread.daemon = True
            self._started = True
            server_thread.start()
            self.find_remote_players()

    def shutdown(self):
        """
        Tell the serve_forever() loop to stop and wait until it does. shutdown() must be called while serve_forever() is running in a different thread otherwise it will deadlock.
        """
        super().shutdown()
        self._started = False

    def find_remote_players(self):
        """
        Seeks other players available on the LAN.

        Broadcasts an IAMHERE opcode over the local network, expected being caught by available other players' servers.
        Waits during 5 seconds for a reply from a hypothetical server, and records its address in the parameter `play_addr`.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._log.debug(
            "Send an IAMHERE message over the LAN through the broadcast address"
        )
        try:
            for broad in self.broad_addr:
                sock.sendto(bytes([opcode.IAMHERE]), (broad, self.port))
        except PermissionError:
            self._log.exception(
                f"{broad} broadcast address is not permitted on this interface by Windows. Please grant access and try again."
            )
            sys.exit(0)

    def check_one_remote(self, addr: str, addr_to_remove: list, lock: threading.Lock):
        """
        Checks if a particular remote player is still available.

        Sends a KEEPALIVE message to the `addr` address. If it does not respond within 5 seconds, adds the address in the `addr_to_remove` list.

        Parameters:
                addr:
                        IP address to check (for instance: "100.50.200.5")
                addr_to_remove:
                        list shared with other threads of all addresses not responding any more
                lock:
                        Lock protecting the access to `addr_to_remove`
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        self._log.debug(f"Check if {addr} is still available")
        sock.sendto(bytes([opcode.KEEPALIVE]), (addr, self.port))
        try:
            reply = sock.recvfrom(1024)
            if reply[0][0] != opcode.KEEPALIVE:
                with lock:
                    self._log.debug(
                        f"Bad answer to keep alive: {addr} is not yet available"
                    )
                    addr_to_remove.append(addr)
            else:
                self._log.debug(f"Confirmation of availability of {reply[1][0]}")
        except TimeoutError:
            with lock:
                self._log.debug(f"Time out to keep alive: {addr} is not yet available")
                addr_to_remove.append(addr)

    def check_remote_players(self):
        """
        Checks for the presence of the remote players.

        Sends a KEEPALIVE message to all known remote players. If one does not respond within 5 seconds, erases its address from the parameter `play_addr`.
        """
        addr_to_remove = list()
        lock = threading.Lock()
        threads = list()
        for addr in self.play_addr:
            threads.append(
                threading.Thread(
                    target=self.check_one_remote,
                    kwargs={
                        "addr": addr,
                        "addr_to_remove": addr_to_remove,
                        "lock": lock,
                    },
                )
            )

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        if len(addr_to_remove) > 0:
            with self.addr_lock:
                self._log.info(
                    f"The following addresses are removed from the list of the remote players: {addr_to_remove}"
                )
                for addr in addr_to_remove:
                    self.play_addr.remove(addr)

        self._log.debug(
            f"The current available players are:\n    {self._local_address} (local)\n    {self._play_addr}"
        )

    def send_once_player_characteristics(self, addr: str, player: Player):
        """
        Sends player characteristics to a particular remote player over the LAN.

        Parameters:
                addr:
                        IPv4 address of a remote player. Must be a valid and already known player's address
                player (domichess.game.Player):
                        Player characteristics to emit.

        Raises:
                ValueError:
                        If `addr`is not a correct or an already known player's address
        """
        if addr in self.play_addr:
            parsed_player = {
                "name": player.name,
                "color": player.color,
                "uuid": player.uuid,
            }
            serialized_player = json.dumps(parsed_player)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._log.debug(f"Send to {addr} all player's characteristics")
            sock.sendto(
                bytes([opcode.PLAYERFULL]) + bytes(serialized_player, "utf-8"),
                (addr, self.port),
            )
        else:
            raise ValueError(f"{addr} is not a correct player's address")

    def send_player_characteristics(self, player: Player):
        """
        Sends player characteristics to all known remote players over the LAN.

        Parameters:
                player (domichess.game.Player):
                        Player characteristics to emit.
        """
        for addr in self.play_addr:
            self.send_once_player_characteristics(addr, player)

    def send_once_player_update(self, addr: str, charact: opcode, value: str | bool):
        """
        Sends one player's characteristic to a particular remote player over the LAN.

        This method is usefull to inform a particular player that one or several characteristics of the local player have changed.

        Parameters:
                addr:
                        IPv4 address of a remote player. Must be a valid and already known player's address
                charact:
                        the characteristic to update. Possible values are: opcode.PLAYERNAME, opcode.PLAYERUUID, opcode.PLAYERCOLOR
                value:
                        the new value of the characteristic. Must be a string for PLAYERNAME or PLAYERUUID, and a boolean for PLAYERCOLOR

        Raises:
                ValueError:
                        If `addr`is not a correct or an already known player's address
                        If `charact` is not of a correct opcode
                TypeError:
                        If `value` does not meet the suitable type

        """
        if (addr in self.play_addr) and (
            charact in [opcode.PLAYERNAME, opcode.PLAYERUUID, opcode.PLAYERCOLOR]
        ):
            if (
                (charact in [opcode.PLAYERNAME, opcode.PLAYERUUID])
                and isinstance(value, str)
            ) or (charact == opcode.PLAYERCOLOR and isinstance(value, bool)):
                serialized_value = json.dumps(value)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._log.debug(
                    f"Send to {addr} the {'color' if charact==opcode.PLAYERCOLOR else 'UUID' if charact==opcode.PLAYERUUID else 'name'}: {'WHITE' if (charact==opcode.PLAYERCOLOR and value) else 'BLACK' if (charact==opcode.PLAYERCOLOR and not value) else value}"
                )
                sock.sendto(
                    bytes([charact]) + bytes(serialized_value, "utf-8"),
                    (addr, self.port),
                )
            else:
                raise TypeError("The provided `value` does not meet the suitable type")
        else:
            if addr not in self.play_addr:
                raise ValueError(f"{addr} is not a correct player's address")
            else:
                raise ValueError("The `charact` is not of a correct opcode")

    def send_player_update(self, charact: opcode, value: str | bool):
        """
        Sends one player's characteristic to all known remote players over the LAN.

        This method is usefull to inform other players that one or several characteristics of the local player have changed.

        Parameters:
                charact:
                        the characteristic to update. Possible values are: opcode.PLAYERNAME, opcode.PLAYERUUID, opcode.PLAYERCOLOR
                value:
                        the new value of the characteristic. Must be a string for PLAYERNAME or PLAYERUUID, and a boolean for PLAYERCOLOR

        Raises:
                ValueError:
                        If `charact` is not of a correct opcode
                TypeError:
                        If `value` does not meet the suitable type

        """
        if charact in [opcode.PLAYERNAME, opcode.PLAYERUUID, opcode.PLAYERCOLOR]:
            if (
                (charact in [opcode.PLAYERNAME, opcode.PLAYERUUID])
                and isinstance(value, str)
            ) or (charact == opcode.PLAYERCOLOR and isinstance(value, bool)):
                for addr in self.play_addr:
                    self.send_once_player_update(addr, charact, value)
            else:
                raise TypeError("The provided `value` does not meet the suitable type")
        else:
            raise ValueError("The `charact` is not of a correct opcode")

    def send_once_game_charact(self, addr: str, charact: opcode, value: str):
        """
        Sends one game's characteristic to a particular remote player over the LAN.

        Parameters:
                addr:
                        IPv4 address of a remote player. Must be a valid and already known player's address
                charact:
                        the characteristic to send. Possible values are: opcode.GAMENAME, opcode.GAMEUUID
                value:
                        the value of the characteristic

        Raises:
                ValueError:
                        If `addr`is not a correct or an already known player's address
                        If `charact` is not of a correct opcode
                TypeError:
                        If `value` does not meet the suitable type
        """
        if (
            (addr in self.play_addr)
            and (charact in [opcode.GAMENAME, opcode.GAMEUUID])
            and (isinstance(value, str))
        ):
            serialized_value = json.dumps(value)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._log.debug(
                f"Send to {addr} the {'name' if charact==opcode.GAMENAME else 'UUID'} of the game: {value}"
            )
            sock.sendto(
                bytes([charact]) + bytes(serialized_value, "utf-8"), (addr, self.port)
            )
        else:
            if addr not in self.play_addr:
                raise ValueError(f"{addr} is not a correct player's address")
            elif charact in [opcode.GAMENAME, opcode.GAMEUUID]:
                raise ValueError("The `charact` is not of a correct opcode")
            else:
                raise TypeError("`value` must be a string")

    def send_game_charact(self, charact: opcode, value: str):
        """
        Sends one game's characteristic to all known remote players over the LAN.

        Parameters:
                charact:
                        the characteristic to send. Possible values are: opcode.GAMENAME, opcode.GAMEUUID
                value:
                        the value of the characteristic

        Raises:
                ValueError:
                        If `charact` is not of a correct opcode
                TypeError:
                        If `value` does not meet the suitable type
        """
        if (charact in [opcode.GAMENAME, opcode.GAMEUUID]) and (isinstance(value, str)):
            for addr in self.play_addr:
                self.send_once_game_charact(addr, charact, value)
        else:
            if charact in [opcode.GAMENAME, opcode.GAMEUUID]:
                raise ValueError("The `charact` is not of a correct opcode")
            else:
                raise TypeError("`value` must be a string")

    def join_game(self, addr: str):
        """
        Informs a remote player that we wish to join his game.

        Parameters:
                addr:
                        IPv4 address of a remote player. Must be a valid and already known player's address

        Raises:
                ValueError:
                        If `addr`is not a correct or an already known player's address
        """
        if addr in self.play_addr:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._log.debug(
                f"Inform {addr} that we wish to join his game named {self.remote_games[addr]}"
            )
            sock.sendto(bytes([opcode.GAMEJOIN]), (addr, self.port))
        else:
            raise ValueError(f"{addr} is not a correct player's address")

    def leave_game(self, addr: str):
        """
        Informs a remote player that we wish to leave (ie: "unjoin") his game.

        Parameters:
                addr:
                        IPv4 address of a remote player. Must be a valid and already known player's address

        Raises:
                ValueError:
                        If `addr`is not a correct or an already known player's address
        """
        if addr in self.play_addr:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._log.debug(
                f"Inform {addr} that we wish to leave his game named {self.remote_games[addr]}"
            )
            sock.sendto(bytes([opcode.GAMELEAVE]), (addr, self.port))
        else:
            raise ValueError(f"{addr} is not a correct player's address")

    def start_game(self, addr: str):
        """
        Informs a remote player who wishes to join our game, that we accept to play with him, and that the game is about to begin.

        Parameters:
                addr:
                        IPv4 address of a remote player. Must be a valid and already known player's address, who previously wished to play our game.

        Raises:
                ValueError:
                        If `addr`is not a correct or an already known player's address, or a player who previously wished to play our game
        """
        if (addr in self.play_addr) and (addr in self.joined_players):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._log.debug(f"Inform {addr} that the game is about to begin")
            sock.sendto(bytes([opcode.GAMESTART]), (addr, self.port))
        else:
            if addr not in self.play_addr:
                raise ValueError(f"{addr} is not a correct player's address")
            else:
                raise ValueError(
                    f"{addr} is a known player, but does not wish to play with us"
                )

    def quit_game(self, addr: str):
        """
        Informs a remote player that we leave the network.

        Parameters:
                addr:
                        IPv4 address of a remote player. Must be a valid and already known player's address

        Raises:
                ValueError:
                        If `addr`is not a correct or an already known player's address
        """
        if addr in self.play_addr:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._log.debug(f"Inform {addr} that we quit the network game")
            sock.sendto(bytes([opcode.QUIT]), (addr, self.port))
        else:
            raise ValueError(f"{addr} is not a correct player's address")

    def quit_game_all(self):
        """
        Informs all remote players that we leave the network.
        """
        for addr in self.play_addr:
            self.quit_game(addr)


class PlayingHandler(StreamRequestHandler):
    """
    Handler instanciated in response to a request to the playing server.
    """
    
    def handle(self):
        """
        Analyses a message sent by a client.
        """
        data = self.request.recv(1024).strip()
        recv_opcode = data[0]
        if recv_opcode == opcode.GAMEFULL:
            game_full = json.loads(str(data[1:], "utf-8"))
            if game_full["uuid"] not in [game["uuid"] for game in self.server.games]:
                with self.server.games_lock:
                    self.server.games.append({"name":game_full["name"], "uuid":game_full["uuid"], chess.WHITE:None, chess.BLACK:None})
                self.server.log.debug(f"A new game named {game_full['name']} is available on the server")
                self.request.sendall(bytes([opcode.SUCCESSFUL]))
            else:
                self.server.log.debug(f"The game named {game_full['name']} is already recorded on the server.")
                self.request.sendall(bytes([opcode.UNSUCCESSFUL]))
        
        elif recv_opcode == opcode.GAMEDELETE:
            game_uuid = json.loads(str(data[1:], "utf-8"))
            game_to_erase = -1
            for rank, game in enumerate(self.server.games):
                if game["uuid"] == game_uuid:
                    game_to_erase = rank
                    break
            if game_to_erase >= 0:
                with self.server.games_lock:
                    del self.server.games[game_to_erase]
                self.server.log.debug(f"Game with UUID = {game_uuid} is deleted.")
                self.request.sendall(bytes([opcode.SUCCESSFUL]))
            else:
                self.server.log.debug(f"Game with UUID = {game_uuid} does not exist and cannot be deleted.")
                self.request.sendall(bytes([opcode.UNSUCCESSFUL]))
        
        elif recv_opcode == opcode.GAMEJOIN:
            game_join = json.loads(str(data[1:], "utf-8"))
            game_to_join = -1
            for rank, game in enumerate(self.server.games):
                if game["uuid"] == game_join["game_uuid"]:
                    game_to_join = rank
                    break
            if game_to_join >= 0:
                if self.server.games[game_to_join][game_join["player_color"]] is not None:
                    self.server.log.warning(f"The {'white' if game_join['player_color'] else 'black'} opponent of the game {self.server.games[game_to_join]['name']} was already designated, and will be replaced by a new one.")
                with self.server.games_lock:
                   self.server.games[game_to_join][game_join["player_color"]] = {"name":game_join["player_name"], "uuid":game_join["player_uuid"], "socket":self.request}
                self.server.log.debug(f"The player {game_join['player_name']} has joined the game {self.server.games[game_to_join]['name']} as {'white' if game_join['player_color'] else 'black'} opponent.")
                self.request.sendall(bytes([opcode.SUCCESSFUL]))
            else:
                self.server.log.warning(f"No game with UUID = {game_join['game_uuid']} available to join.")
                self.request.sendall(bytes([opcode.UNSUCCESSFUL]))
        
        elif recv_opcode == opcode.MOVE:
            move = json.loads(str(data[1:], "utf-8"))
            game_to_move = -1
            for rank, game in enumerate(self.server.games):
                if (game[chess.WHITE] is not None) and (game[chess.WHITE]["uuid"] == move["player_uuid"]):
                    color = chess.WHITE
                    game_to_move = rank
                    break
                elif (game[chess.BLACK] is not None) and (game[chess.BLACK]["uuid"] == move["player_uuid"]):
                    color = chess.BLACK
                    game_to_move = rank
                    break
            if game_to_move >= 0:
                if self.server.games[game_to_move][not color] is not None:
                    move_to_send = {"player_uuid": move["player_uuid"], "move":move["move"]}
                    serialized_move = json.dumps(move_to_send)
                    sock = self.server.games[game_to_move][not color]["socket"]
                    try:
                        sock.sendall(bytes([opcode.MOVE]) + bytes(serialized_move, "utf-8"))
                        self.server.log.debug(f"The move {move['move']} has been successfully relayed to the opponent.")
                        self.request.sendall(bytes([opcode.SUCCESSFUL]))
                    except OSError as err:
                        self._log.error(f"Network error: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                        except OSError:
                            pass # Already disconnected: nothing else to do anymore
                        self.server.games[game_to_move][not color]["socket"] = None
                        self.server.log.warning(f"The move {move['move']} has not been relayed because the opponent is not available.")
                        self.request.sendall(bytes([opcode.UNREACHABLE]))
                else:
                    self.server.log.warning(f"The move {move['move']} has not been relayed because the opponent is not available.")
                    self.request.sendall(bytes([opcode.UNREACHABLE]))
            else:
                self.server.log.warning(f"The player with UUID = {move['player_uuid']} is not known, his move {move['move']} has not been relayed.")
                self.request.sendall(bytes([opcode.UNSUCCESSFUL]))
                
        elif recv_opcode == opcode.CLAIM:
            claim = json.loads(str(data[1:], "utf-8"))
            game_to_claim = -1
            for rank, game in enumerate(self.server.games):
                if (game[chess.WHITE] is not None) and (game[chess.WHITE]["uuid"] == claim["player_uuid"]):
                    color = chess.WHITE
                    game_to_claim = rank
                    break
                elif (game[chess.BLACK] is not None) and (game[chess.BLACK]["uuid"] == claim["player_uuid"]):
                    color = chess.BLACK
                    game_to_claim = rank
                    break
            if game_to_claim >= 0:
                if self.server.games[game_to_claim][not color] is not None:
                    claim_to_send = {"player_uuid": claim["player_uuid"], "claim":claim["claim"]}
                    serialized_claim = json.dumps(claim_to_send)
                    sock = self.server.games[game_to_claim][not color]["socket"]
                    try:
                        sock.sendall(bytes([opcode.CLAIM]) + bytes(serialized_claim, "utf-8"))
                        self.server.log.debug(f"The claim {claim['claim']} has been successfully relayed to the opponent.")
                        self.request.sendall(bytes([opcode.SUCCESSFUL]))
                    except OSError as err:
                        self._log.error(f"Network error: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                        except OSError:
                            pass # Already disconnected: nothing else to do anymore
                        self.server.games[game_to_claim][not color]["socket"] = None
                        self.server.log.warning(f"The claim {claim['claim']} has not been relayed because the opponent is not available.")
                        self.request.sendall(bytes([opcode.UNREACHABLE]))
                else:
                    self.server.log.warning(f"The claim {claim['claim']} has not been relayed because the opponent is not available.")
                    self.request.sendall(bytes([opcode.UNREACHABLE]))
            else:
                self.server.log.warning(f"The player with UUID = {claim['player_uuid']} is not known, his claim {claim['claim']} has not been relayed.")
                self.request.sendall(bytes([opcode.UNSUCCESSFUL]))
		
        elif recv_opcode == opcode.WITHDRAWAL:
            abord = json.loads(str(data[1:], "utf-8"))
            game_to_abord = -1
            for rank, game in enumerate(self.server.games):
                if (game[chess.WHITE] is not None) and (game[chess.WHITE]["uuid"] == abord["player_uuid"]):
                    color = chess.WHITE
                    game_to_abord = rank
                    break
                elif (game[chess.BLACK] is not None) and (game[chess.BLACK]["uuid"] == abord["player_uuid"]):
                    color = chess.BLACK
                    game_to_abord = rank
                    break
            if game_to_abord >= 0:
                if self.server.games[game_to_abord][not color] is not None:
                    abord_to_send = {"player_uuid": abord["player_uuid"]}
                    serialized_abord = json.dumps(abord_to_send)
                    sock = self.server.games[game_to_abord][not color]["socket"]
                    try:
                        sock.sendall(bytes([opcode.GAMEABORD]) + bytes(serialized_abord, "utf-8"))
                        self.server.log.debug(f"The withdrawal has been successfully relayed to the opponent.")
                        self.request.sendall(bytes([opcode.SUCCESSFUL]))
                    except OSError as err:
                        self._log.error(f"Network error: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                        except OSError:
                            pass # Already disconnected: nothing else to do anymore
                        self.server.games[game_to_abord][not color]["socket"] = None
                        self.server.log.warning("The withdrawal has not been relayed because the opponent is not available.")
                        self.request.sendall(bytes([opcode.UNREACHABLE]))
                else:
                    self.server.log.warning("The withdrawal has not been relayed because the opponent is not available.")
                    self.request.sendall(bytes([opcode.UNREACHABLE]))
            else:
                self.server.log.warning(f"The player with UUID = {abord['player_uuid']} is unknown, his abording has not been relayed.")
                self.request.sendall(bytes([opcode.UNSUCCESSFUL]))

        elif recv_opcode == opcode.KEEPALIVE:
            self.server.log.debug(f"Receipt of a KEEPALIVE from {self.client_address[0]}")

class PlayingServer(ThreadingTCPServer):
    """
    This class implements a server for playing a game between 2 opponents. It inherits the [socketserver.ThreadingTCPServer class](https://docs.python.org/3/library/socketserver.html#socketserver.ThreadingTCPServer).
    
    Once the method `server_start()` is called, this server waits for a connexion on the given port, on all IP interfaces. In this case, all methods beginning by `server_` or `client_` are available.
    
    Please note that this class can also be used as a client: for that, the `server_start()` should simply not be called. In this case, all methods beginning by `client_` are available, but not those beginning by `server_`.
    
    Parameters:
        port:
            The port number on which the server is listening to.
        logger:
            The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.
    
    Attributes:
        port:
            The port number on which the server is listening to. **read-only**
        started:
            `True` if the server is running. `False` otherwise. **read-only**
        games:
            List of the games currently playing. Each value is a dictionnary {"name": name_of_the_game, "uuid": UUID_of_the_game, chess.WHITE: player|None, chess.BLACK: player|None}, with *player* itself a dictionnary {"name": name_of_the_player, "uuid": UUID_of_the_player, "socket": socket_connected_to_the_remote_player}. **read-only** (but mutable)
        client_socket:
            Socket connected to the remote server, in case of usage of this class as a client.
        client_is_connected:
            True if the client is connected to the server, False otherwise. **read-only**
        client_game:
            Game played by the client.
        log (logging.Logger):
            Logger used to track events that append when the instance is running. Child of the `logger` provided, or a fake logger with a null handler. **read-only**
    """
    def __init__(self, port: int, logger: logging.Logger|None = None):
        if logger is None:
            self._log = logging.getLogger("PlayingServer")
            self._log.addHandler(logging.NullHandler())
        else:
            self._log = logger.getChild("PlayingServer")

        self._log.debug("--- Playing Server initialization ---")
        
        super().__init__(("", port), RequestHandlerClass=PlayingHandler, bind_and_activate=False)
        
        self._started = False
        self._port = port
        
        self._games = [{"name":"", "uuid":"", chess.WHITE:None, chess.BLACK:None}]
        self.games_lock = threading.Lock()
        
        self._client_socket = None
        self._client_is_connected = False
        self._client_game = None
    
    @property
    def started(self) -> bool:
        # `True` if the server is running. `False` otherwise.
        return self._started
    
    @property
    def port(self) -> int:
        # The port number on which the server is listening to.
        return self._port
        
    @property
    def log(self) -> logging.Logger:
        # Logger used to track events that append when the instance is running. Child of the `logger` provided, or a fake logger with a null handler.
        return self._log
    
    @property
    def games(self) -> list:
        # List of the games currently playing
        return self._games
    
    @property
    def client_socket(self) -> socket.socket:
        # Socket connected to the remote server, in case of usage of this class as a client.
        return self._client_socket
    
    @client_socket.setter
    def client_socket(self, value):
        if isinstance(value, socket.socket):
            self._client_socket = value
        else:
            self._log.error("`client_socket` only accepts socket.socket objects.")
    
    @property
    def client_is_connected(self) -> bool:
        # True if the client is connected to the server, False otherwise.
        return self._client_is_connected
    
    @property
    def client_game(self) -> Game:
        # Game played by the client
        return self._client_game
    
    @client_game.setter
    def client_game(self, value):
        if isinstance(value, Game):
            self._client_game = value
        else:
            self._log.error("`client_game` only accepts domichess.game.Game objects.")
    
    ### Server only methods ###

    def server_start(self, blocking:bool = False):
        """
        Starts the server and listens to on all IP interfaces.

        If `blocking`is False (the default), the server is executed in a separated thread - and then the method returns immediately. If True, the function blocks until the method `server_shutdown()` is called in a different thread.

        Parameters:
            blocking:
                indicates whether the method blocks (True) or returns immediately (False)
        """
        if not self._started:
            super().server_bind()
            super().server_activate()
            
            if blocking:
                self._log.info("Server activated in blocking mode. Stop it with CTRL-C.")
                self._log.info(f"Server listening at port {self.port}")
                self._started = True
                self.serve_forever()
            else:
                self._log.info("Server activated in non-blocking mode.")
                self._log.info(f"Server listening at port {self.port}")
                server_thread = threading.Thread(target=self.serve_forever)
                server_thread.daemon = True
                self._started = True
                server_thread.start()
    
    def server_shutdown(self):
        """
        Tells the listening server loop to stop and wait until it does. `server_shutdown()` must be called while listening server loop is running in a different thread otherwise it will deadlock.
        """
        if self._started:
            super().shutdown()
            self._started = False
        else:
            self._log.warning("The server method `server_shutdown()` has been called (with no effect) in a `PlayingServer` instance in *client* state, or the server has been already shutted down.")
        
    
    ### Client methods ###
    
    def client_connect(self, addr:str, timeout:int|float|None = socket.getdefaulttimeout()) -> bool:
        """
        Connects to the server hosted at the given IPv4 address.
        
        In case of a successful connection, stores the socket in the `client_socket` attribute.
        
        Parameters:
            addr:
                IPv4 address of the remote server (ex: `100.50.200.5`)
            timeout:
                Set a timeout (in seconds) on the created socket instance before attempting to connect. If no timeout is supplied, the global default timeout setting returned by `[socket.getdefaulttimeout()](https://docs.python.org/3/library/socket.html?highlight=socket#socket.getdefaulttimeout)` is used (None by default, meaning that the socket is put in blocking mode).
        
        Returns:
            True if the connection is a success, False otherwise.
        """
        try:
            self._client_socket = socket.create_connection((addr, self.port), timeout=timeout)
            self._client_socket.settimeout(timeout)
        except TimeoutError:
            self._log.error("Time out on connection attempt.")
            self._client_is_connected = False
        except ConnectionRefusedError:
            self._log.error("Connection attempt refused by the server.")
            self._client_is_connected = False
        except ConnectionAbordedError:
            self._log.error("Connection attempt aborded by the server.")
            self._client_is_connected = False
        except Exception as e:
            self._log.error(e)
            self._client_is_connected = False
        else:
            self._log.info(f"Client successfully connected to server hosted at {addr}.")
            self._client_is_connected = True
        finally:
            return self._client_is_connected
    
    def client_disconnect(self):
        """
        Shuts down and closes the connection to the server.
        
        Can be called safely even if the socket is already disconnected.
        """
        try:
            self._client_socket.shutdown(socket.SHUT_RDWR)
            self._client_socket.close()
        except OSError:
            pass # Already disconnected: nothing else to do anymore
        self._client_is_connected = False
        self._log.info("Client successfully disconnected from the server.")
    
    def client_send(self, msg_opcode:opcode, message:dict|str|int|float|None) -> int:
        """
        Sends a message to the connected server.
        
        The message must be identified by an opcode, and should be [json](https://docs.python.org/3/library/json.html) serializable.
        The format of `message` shall meets the following requirements, depending on the value of `opcode`:
        
        |  opcode    |    message format        |
        | ---------- | ------------------------ |
        | KEEPALIVE  | None                     |
        | GAMEFULL   | {"uuid":str, "name":str} |
        | GAMEJOIN   | {"game_uuid":str, "player_color":bool, "player_name":str, "player_uuid":str}  |
        | GAMEDELETE | str (UUID of the game to delete)  |
        | GAMEABORD  | {"player_uuid": str}              |
        | MOVE       | {"player_uuid": str, "move":str}  |
        | CLAIM      | {"player_uuid": str, "claim":int} |
        
        The value returned by this method is an error code (except `0`), identifying the cause of an unsuccessful attempt of sending a message. The possible values are:
        
        | code  |  meaning                             |
        | ----- | ------------------------------------ |
        | 0     | No error - Message successfully sent |
        | 1     | Unknown opcode                       |
        | 2     | Bad format for the message           |
        | 3     | `message` is not serializable        |
        | 4     | The link to the server is temporarily unavailable. Please try again later |
        | 5     | The link to the server is not connected (`client_is_connected` is`False`) |
        | 6     | Broken Pipe Error - The socket has been shutdown for writing by the server |
        | 7     | Connection reset by the server, due to a crash or an unclean shutdown |
        | 8     | Operation timed out                   |
        | 9     | Other network error                   |
        
        From the value `6` onwards, `client_disconnect()` is internally executed before handing over. Subsequent calls to the method will return error `5` systematically if no action is taken in the meantime to resolve the problem.
        It is safe to retry the method several times after an error `4`, but the systematic return of this value is symptomatic of a data flow bottleneck, and should be managed by the calling function by setting up waiting times between each data transmission, for example.
        The error `8` is only relevant if the socket was not initialized in blocking mode.
        Please note that only issues regarding the connection between the current client and the server are detected; the message can be successfully sent even if there is a connection failure between the server and the opponent client.
        
        Parameters:
            msg_opcode:
                opcode identifying the nature of the message to send
            message:
                message to send
        
        Returns:
            Error code or `0` if the message is successfully sent.
        """
        if msg_opcode not in [opcode.KEEPALIVE, opcode.GAMEFULL, opcode.GAMEJOIN, opcode.GAMEDELETE, opcode.GAMEABORD, opcode.MOVE, opcode.CLAIM]:
            self._log.error(f"{msg_opcode} is not a compatible opcode")
            return 1
        elif (msg_opcode == opcode.KEEPALIVE) and (message is not None):
            self._log.error(f"{message} is not a message compatible with the opcode KEEPALIVE")
            return 2
        elif (msg_opcode == opcode.GAMEFULL) and ((not isinstance(message,dict)) or ("uuid" not in message) or ("name" not in message)):
            self._log.error(f"{message} is not a message compatible with the opcode GAMEFULL")
            return 2
        elif (msg_opcode == opcode.GAMEJOIN) and ((not isinstance(message,dict)) or ("game_uuid" not in message) or ("player_color" not in message) or ("player_name" not in message) or ("player_uuid" not in message)):
            self._log.error(f"{message} is not a message compatible with the opcode GAMEJOIN")
            return 2
        elif (msg_opcode == opcode.GAMEDELETE) and (not isinstance(message,str)):
            self._log.error(f"{message} is not a message compatible with the opcode GAMEDELETE")
            return 2
        elif (msg_opcode == opcode.GAMEABORD) and ((not isinstance(message,dict)) or ("player_uuid" not in message)):
            self._log.error(f"{message} is not a message compatible with the opcode GAMEABORD")
            return 2
        elif (msg_opcode == opcode.MOVE) and ((not isinstance(message,dict)) or ("player_uuid" not in message) or ("move" not in message)):
            self._log.error(f"{message} is not a message compatible with the opcode MOVE")
            return 2
        elif (msg_opcode == opcode.CLAIM) and ((not isinstance(message,dict)) or ("player_uuid" not in message) or ("claim" not in message)):
            self._log.error(f"{message} is not a message compatible with the opcode CLAIM")
            return 2
        else:
            try:
                json_msg = json.dumps(message)
            except TypeError:
                self._log.error(f"{message} is not serializable")
                return 3
            if not self._client_is_connected:
                self._log.error("The server is not connected")
                return 5
            else:
                try:
                    self._client_socket.sendall(bytes([msg_opcode]) + bytes(json_msg, "utf-8"))
                except BlockingIOError:
                    self._log.error("The link to the server is temporarily unavailable. Please try again later")
                    return 4
                except BrokenPipeError:
                    self._log.error("Broken Pipe Error - The socket has been shutdown for writing by the server")
                    self.client_disconnect()
                    return 6
                except ConnectionResetError:
                    self._log.error("Connection reset by the server, due to a crash or an unclean shutdown")
                    self.client_disconnect()
                    return 7
                except TimeoutError:
                    self._log.error("Operation timed out")
                    self.client_disconnect()
                    return 8
                except OSError as err:
                    self._log.error(f"Network error: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    self.client_disconnect()
                    return 9
                else:
                    self._log.debug("Message successfully sent")
                    return 0
    
    def client_create_new_game(self) -> int:
        """
        Creates a new game on the connected server.
        
        The characteristics of the game are those of the `client_game` attribute, which must therefore be correctly initialized before calling this method.
        
        Returns:
            `0` if the game has been created successfully, `1` if the game has not been created because the UUID already exists on the server, and `-1` for no game creation due to other reasons.
        """
        if self._client_game is None:
            self._log.error("The `client_game` is not correctly initialized.")
            return -1
        else:
            msg_opcode = opcode.GAMEFULL
            message = {"uuid":self._client_game.uuid, "name":self._client_game.name}
            repeat_max = 3
            repeat = 0
            while repeat < repeat_max:
                return_code = self.client_send(msg_opcode,message)
                if return_code == 4:
                    time.sleep(0.1)
                    repeat += 1
                elif return_code not in [0,4]:
                    self._log.error(f"The game {self._client_game.name} is not created due to a connection issue with the server.")
                    return -1
                else:
                    break
            if return_code == 4:
                self._log.error(f"The game {self._client_game.name} is not created due to a data flow bottleneck when communicating with the server.")
                return -1
            else:
                try:
                    data = self._client_socket.recv(1024).strip()
                except OSError as err:
                    self._log.error(f"Network error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    self.client_disconnect()
                    return -1
                except:
                    self._log.error(f"Unknown error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    return -1
                else:
                    recv_opcode = data[0]
                    if recv_opcode == opcode.SUCCESSFUL:
                        self._log.debug(f"The game {self._client_game.name} is successfully created")
                        return 0
                    elif recv_opcode == opcode.UNSUCCESSFUL:
                        self._log.debug(f"The game {self._client_game.name} is not created because the UUID is already recorded on the server")
                        return 1
                    else:
                        self._log.error("Receipt of an unexpected opcode")
                        return -1
    
    def client_delete_game(self, game_uuid:str) -> int:
        """
        Deletes game on the connected server.
        
        The characteristics of the player are those of the `client_game` attribute, which must therefore be correctly initialized before calling this method.
        
        Parameters:
            game_uuid:
                UUID of the game
        
        Returns:
            `0` if the game has been deleted successfully, `1` if the game does not exist on the server, and `-1` for no game deletion due to other reasons.
        """
        if not isinstance(game_uuid, str):
            self._log.error("The game is not deleted because the game UUID is not a string.")
            return -1
        else:
            msg_opcode = opcode.GAMEDELETE
            message = game_uuid
            repeat_max = 3
            repeat = 0
            while repeat < repeat_max:
                return_code = self.client_send(msg_opcode,message)
                if return_code == 4:
                    time.sleep(0.1)
                    repeat += 1
                elif return_code not in [0,4]:
                    self._log.error(f"The game {game_uuid} is not deleted due to a connection issue with the server.")
                    return -1
                else:
                    break
            if return_code == 4:
                self._log.error(f"The game {game_uuid} is not deleted due to a data flow bottleneck when communicating with the server.")
                return -1
            else:
                try:
                    data = self._client_socket.recv(1024).strip()
                except OSError as err:
                    self._log.error(f"Network error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    self.client_disconnect()
                    return -1
                except:
                    self._log.error(f"Unknown error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    return -1
                else:
                    recv_opcode = data[0]
                    if recv_opcode == opcode.SUCCESSFUL:
                        self._log.debug(f"The game {game_uuid} is successfully deleted")
                        return 0
                    elif recv_opcode == opcode.UNSUCCESSFUL:
                        self._log.debug(f"The game {game_uuid} does not exist and cannot be deleted on the server")
                        return 1
                    else:
                        self._log.error("Receipt of an unexpected opcode")
                        return -1
    
    def client_join_game(self, game_uuid:str) -> int:
        """
        Joins a game on the connected server.
        
        The characteristics of the player joining the game are deduced from the `client_game` attribute, which must therefore be correctly initialized before this method is called. This is the player who is not of type `Type.NETWORK`.
        
        Parameters:
            game_uuid:
                UUID of the game
        
        Returns:
            `0` if the game has been joined successfully, `1` if the game does not exist on the server, and `-1` if the game has not been joined due to other reasons.
        """
        if self._client_game is None:
            self._log.error("The `client_game` attribute is not correctly initialized.")
            return -1
        elif not isinstance(game_uuid, str):
            self._log.error("Unable to join the game because the game UUID not a string.")
            return -1
        else:
            compliant_players = [player for player in self._client_game.players if player.type in [Type.HUMAN, Type.CPU]]
            if len(compliant_players) == 2:
                self._log.error("No network opponent in the current game")
                return -1
            elif len(compliant_players) == 0:
                self._log.error("No available player detected")
                return -1
            else:
                player = compliant_players[0]
                msg_opcode = opcode.GAMEJOIN
                message = {"game_uuid":game_uuid, "player_color":player.color, "player_name":player.name, "player_uuid":player.uuid}
                repeat_max = 3
                repeat = 0
                while repeat < repeat_max:
                    return_code = self.client_send(msg_opcode,message)
                    if return_code == 4:
                        time.sleep(0.1)
                        repeat += 1
                    elif return_code not in [0,4]:
                        self._log.error(f"The game {game_uuid} is not joined due to a connection issue with the server.")
                        return -1
                    else:
                        break
                if return_code == 4:
                    self._log.error(f"The game {game_uuid} is not joined due to a data flow bottleneck when communicating with the server.")
                    return -1
                else:
                    try:
                        data = self._client_socket.recv(1024).strip()
                    except OSError as err:
                        self._log.error(f"Network error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                        self.client_disconnect()
                        return -1
                    except:
                        self._log.error(f"Unknown error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                        return -1
                    else:
                        recv_opcode = data[0]
                        if recv_opcode == opcode.SUCCESSFUL:
                            self._log.debug(f"The game {game_uuid} is successfully joined")
                            self._client_game.uuid = game_uuid
                            return 0
                        elif recv_opcode == opcode.UNSUCCESSFUL:
                            self._log.debug(f"The game {game_uuid} does not exist and cannot be joined")
                            return 1
                        else:
                            self._log.error("Receipt of an unexpected opcode")
                            return -1
    
    def client_move(self, move:chess.Move, wait_for_reply:bool = True) -> dict:
        """
        Informs the opponent of the half-move made by the current, local player, and optionnaly waits for its reply (ie: the following half_move or a claim).
        
        The UUID of the player is deduced from the `client_game` attribute, which must therefore be correctly initialized before this method is called. This is the player who is not of type `Type.NETWORK`.
        
        Parameters:
            move:
                Half-move of the current, local player
            wait_for_reply:
                If `True` (the default), the methods waits for an error or a reply from the opponent. 3 kinds of reply are expected: another half-move, a claim for a draw, or a withdrawal. If `False`, the method returns immediately after the aknowledge of a succesful sending (or after an error).
        
        returns:
            If `wait_for_reply` is `True` (the default): a dictionnary meeting the following format: {"err_code":`err_code`, "reply_type":`reply_type`,"data":`data`}.
            The possible values are:
            
            |   Variable   |                    Possible values                         |
            | ------------ | ---------------------------------------------------------- |
            | `err_code`   | `0` if the half-move has been sent successfully            |
            |              | `1` if the opponent is unreachable                         |
            |              | `-1` if the half-move has not been sent for another reason |
            | `reply_type` | None if an error has occured (`err_code` = 1 or -1)        |
            |              | `0` if the reply is the next half-move of the opponent     |
            |              | `1` if the reply is a claim                                |
            |              | `2` if the reply is the withdrawal of the opponent         |
            | `data`       | a `chess.Move` object if `reply_type` = 0                  |
            |              | `Draw.THREEFOLD` or `Draw.FIFTY` if `reply_type` = 1       |
            |              | None if `reply_type` = 2 or `reply_type` is None           |
                        
            If `wait_for_reply` is `False`: a dictionnary meeting the following format: {"err_code":`err_code`}.
            The possible values are:
            
            |   Variable   |                    Possible values                         |
            | ------------ | ---------------------------------------------------------- |
            | `err_code`   | `0` if the half-move has been sent successfully            |
            |              | `1` if the opponent is unreachable                         |
            |              | `-1` if the half-move has not been sent for another reason |
            
        """
        if self._client_game is None:
            self._log.error("The `client_game` attribute is not correctly initialized.")
            return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
        elif not isinstance(move, chess.Move):
            self._log.error("The move has not the right type.")
            return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
        else:
            compliant_players = [player for player in self._client_game.players if player.type in [Type.HUMAN, Type.CPU]]
            if len(compliant_players) == 2:
                self._log.error("No network opponent in the current game")
                return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
            elif len(compliant_players) == 0:
                self._log.error("No available player detected")
                return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
            else:
                player = compliant_players[0]
                msg_opcode = opcode.MOVE
                message = {"player_uuid":player.uuid, "move":move.uci()}
                repeat_max = 3
                repeat = 0
                while repeat < repeat_max:
                    return_code = self.client_send(msg_opcode,message)
                    if return_code == 4:
                        time.sleep(0.1)
                        repeat += 1
                    elif return_code not in [0,4]:
                        self._log.error(f"Connection issue with the server.")
                        return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                    else:
                        break
                if return_code == 4:
                    self._log.error(f"Data flow bottleneck when communicating with the server.")
                    return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                else:
                    try:
                        data = self._client_socket.recv(1024).strip()
                    except OSError as err:
                        self._log.error(f"Network error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                        self.client_disconnect()
                        return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                    except:
                        self._log.error(f"Unknown error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                        return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                    else:
                        recv_opcode = data[0]
                        if recv_opcode == opcode.SUCCESSFUL:
                            self._log.debug(f"The move {move.uci()} has been successfully sent")
                            if not wait_for_reply:
                                return {"err_code":0}
                        elif (recv_opcode == opcode.UNSUCCESSFUL) or (recv_opcode == opcode.UNREACHABLE):
                            self._log.debug(f"The move {move.uci()} has not been sent correctly")
                            return {"err_code":1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                        else:
                            self._log.error("Receipt of an unexpected opcode")
                            return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                        
                        if wait_for_reply:
                            try:
                                data = self._client_socket.recv(1024).strip()
                            except OSError as err:
                                self._log.error(f"Network error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                                self.client_disconnect()
                                return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                            except:
                                self._log.error(f"Unknown error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                                return {"err_code":-1,"reply_type":None,"data":None} if wait_for_reply else {"err_code":-1}
                            else:
                                recv_opcode = data[0]
                                if recv_opcode == opcode.MOVE:
                                    msg = json.loads(str(data[1:], "utf-8"))
                                    self._log.debug(f"Receipt of the move {msg['move']}")
                                    return {"err_code":0,"reply_type":0,"data":chess.Move.from_uci(msg["move"])}
                                elif recv_opcode == opcode.CLAIM:
                                    msg = json.loads(str(data[1:], "utf-8"))
                                    self._log.debug(f"Receipt of a claim for a draw due to the following reason: {'Fifty-move rule' if msg['claim'] == Draw.FIFTY else 'Threefold repetition'}")
                                    return {"err_code":0,"reply_type":1,"data":msg["claim"]}
                                elif recv_opcode == opcode.WITHDRAWAL:
                                    msg = json.loads(str(data[1:], "utf-8"))
                                    self._log.debug(f"Receipt of a withdrawal")
                                    return {"err_code":0,"reply_type":2,"data":None}
    
    def client_claim(self, claim:int) -> int:
        """
        Claims for a draw.
        
        The UUID of the player is deduced from the `client_game` attribute, which must therefore be correctly initialized before this method is called. This is the player who is not of type `Type.NETWORK`.
        
        Parameters:
            claim:
                `Draw.FIFTY` for a claim according to the fifty-move rule, or `Draw.THREEFOLD` for a claim follwing a threefold repetition.
        
        Returns:
            `0` if the claim has been sent successfully, `1` if the player is not registred on the server, and `-1` if the claim has not been sent due to other reasons.
        """
        compliant_players = [player for player in self._client_game.players if player.type in [Type.HUMAN, Type.CPU]]
        if len(compliant_players) == 2:
            self._log.error("No network opponent in the current game")
            return -1
        elif len(compliant_players) == 0:
            self._log.error("No available player detected")
            return -1
        else:
            player = compliant_players[0]
            msg_opcode = opcode.CLAIM
            message = {"player_uuid":player.uuid}
            repeat_max = 3
            repeat = 0
            while repeat < repeat_max:
                return_code = self.client_send(msg_opcode,message)
                if return_code == 4:
                    time.sleep(0.1)
                    repeat += 1
                elif return_code not in [0,4]:
                    self._log.error(f"Connection issue with the server.")
                    return -1
                else:
                    break
            if return_code == 4:
                self._log.error(f"Data flow bottleneck when communicating with the server.")
                return -1
            else:
                try:
                    data = self._client_socket.recv(1024).strip()
                except OSError as err:
                    self._log.error(f"Network error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    self.client_disconnect()
                    return -1
                except:
                    self._log.error(f"Unknown error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    return -1
                else:
                    recv_opcode = data[0]
                    if recv_opcode == opcode.SUCCESSFUL:
                        self._log.debug(f"The CLAIM message was successfully received by the opponent.")
                        return 0
                    elif recv_opcode == opcode.UNSUCCESSFUL:
                        self._log.warning("The current player is not registred on the server: no claim to send")
                        return 1
                    elif recv_opcode == opcode.UNREACHABLE:
                        self._log.warning("The CLAIM message was sent to the server, but was not received by the opponent.")
                        return -1
                    else:
                        self._log.error("Receipt of an unexpected opcode")
                        return -1
    
    def client_abord(self) -> int:
        """
        Abords the current game.
        
        The UUID of the player is deduced from the `client_game` attribute, which must therefore be correctly initialized before this method is called. This is the player who is not of type `Type.NETWORK`.
        
        Returns:
            `0` if the game has been aborded successfully, `1` if the player is not registred on the server, and `-1` if the game has not been aborded due to other reasons.
        """
        compliant_players = [player for player in self._client_game.players if player.type in [Type.HUMAN, Type.CPU]]
        if len(compliant_players) == 2:
            self._log.error("No network opponent in the current game")
            return -1
        elif len(compliant_players) == 0:
            self._log.error("No available player detected")
            return -1
        else:
            player = compliant_players[0]
            msg_opcode = opcode.WITHDRAWAL
            message = {"player_uuid":player.uuid}
            repeat_max = 3
            repeat = 0
            while repeat < repeat_max:
                return_code = self.client_send(msg_opcode,message)
                if return_code == 4:
                    time.sleep(0.1)
                    repeat += 1
                elif return_code not in [0,4]:
                    self._log.error(f"Connection issue with the server.")
                    return -1
                else:
                    break
            if return_code == 4:
                self._log.error(f"Data flow bottleneck when communicating with the server.")
                return -1
            else:
                try:
                    data = self._client_socket.recv(1024).strip()
                except OSError as err:
                    self._log.error(f"Network error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    self.client_disconnect()
                    return -1
                except:
                    self._log.error(f"Unknown error during reply receipt: {errno.errorcode[err.errno]} ({os.strerror(err.errno)})")
                    return -1
                else:
                    recv_opcode = data[0]
                    if recv_opcode == opcode.SUCCESSFUL:
                        self._log.debug(f"The WITHDRAWAL message was successfully received by the opponent.")
                        return 0
                    elif recv_opcode == opcode.UNSUCCESSFUL:
                        self._log.warning("The current player is not registred on the server: no game to abord")
                        return 1
                    elif recv_opcode == opcode.UNREACHABLE:
                        self._log.warning("The WITHDRAWAL message was sent to the server, but was not received by the opponent.")
                        return -1
                    else:
                        self._log.error("Receipt of an unexpected opcode")
                        return -1
    
    def _client_repeated_keepalive(self):
        """
        Sends out regular KEEPALIVE signals to the server.
        
        Calculates the frequency from the connection timeout, so that KEEPALIVE is transmitted before the timeout expires. This methods returns when the connection is closed.
        """
        period = self._client_socket.gettimeout()*0.75
        msg_opcode = opcode.KEEPALIVE
        message = None
        while self._client_is_connected:
            time.sleep(period)
            return_code = self.client_send(msg_opcode,message)
    
    def client_start_keepalive(self):
        """
        Starts sending repeated KEEPALIVE signals in another thread, and returns immediately.
        """
        threading.Thread(target=self._client_repeated_keepalive, daemon=True).start()

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
