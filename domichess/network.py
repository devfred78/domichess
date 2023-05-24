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
import ipaddress
import json
import logging
import socket
from socketserver import ThreadingUDPServer, DatagramRequestHandler
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
from domichess import Type
from domichess.game import Player

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
    GAMEJOIN = auto()  # Join the remote game
    GAMELEAVE = auto()  # Leave the remote game
    GAMESTART = auto()  # The local game is about to start
    QUIT = auto()  # Quit the network


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
                    The port number on which the server is listenning to.
            server_port:
                    If you want to specify a distinct port for the current server. Mainly for test or investigation purposes. In most cases leave it unmodified.
            logger:
                    The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.

    Attributes:
            local_address:
                    IPv4 address of the local host. **read-only**
            port:
                    The port number on which the server is listenning to. **read-only**
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
        # The port number on which the server is listenning to.
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

        If `blocking`is False (the default), the server is executed in a separated thread - and so the method returns immediately. If True, the function blocks until the method `shutdown()`is called in a different thread.

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
