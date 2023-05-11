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
	Module aiming to test the Finding Player management over the LAN
"""

import logging
import os
import pathlib
import queue
import sys
import threading
import time

import chess
from colorlog import ColoredFormatter

if __name__ == "__main__":
	sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
	import domichess
	import domichess.network
else:
	from .. import domichess
	from ..domichess import network

# Functions
#----------

def execute_UDP_server(call_queue:queue.Queue, stop_event:threading.Event, port:int, check_period:int, server_port:int|None = None, autostart:bool = True, logger:logging.Logger|None = None):
	"""
	Executes endlessely the UDP server.
	
	Blocks until interrupted by setting the `stop_event`: this function should be called in a separated thread.
	
	Parameters:
		call_queue:
			Queue to provide usefull methods and attributes to the parent thread
		stop_event:
			Event to set for stopping the server
		port:
			The port number on which the server is listenning to.
		check_period:
			Period, in seconds, for checking whether remote clients are still alive
		server_port:
			If you want to specify a distinct port for the current server. Mainly for test or investigation purposes. In most cases leave it unmodified.
		autostart:
			If `True` (the default), the server starts automatically. Otherwise, a call to the method `start()` is necessary.
		logger:
			The parent logger used to track events that append when the instance is running. Mainly for status monitoring or fault investigation purposes. If None (the default), no event is tracked.
	"""
	# Start the server
	finder_server = domichess.network.LANFinderServer(port = port, server_port = server_port, logger = logger)
	if autostart:
		finder_server.start()
	
	# Send usefull attributes to the parent thread
	call_queue.put(finder_server.started)
	call_queue.put(finder_server.local_address)
	call_queue.put(finder_server.play_addr)
	
	# Send usefull methods to the parent thread
	call_queue.put(finder_server.start)
	call_queue.put(finder_server.find_remote_players)
	call_queue.put(finder_server.check_remote_players)
	call_queue.put(finder_server.send_player_characteristics)
	call_queue.put(finder_server.send_player_update)
	
	# loop indefinitely (unless interupted)
	while not stop_event.is_set():
		time.sleep(check_period)
		if stop_event.is_set():
			break
		if finder_server.started:
			finder_server.check_remote_players()
	if finder_server.started:
		finder_server.shutdown()
	

# Main function
#--------------
def main():
	""" Main program execution"""
	
	print("***********************************************************")
	print("*                     Network Test n°2                    *")
	print("*                                                         *")
	print("*     Test the finding player management over the LAN     *")
	print("*     with some player's characteristics                  *")
	print("***********************************************************")
	print("")
	# Define the port
	port = "port"
	while not (port.isdigit() and (int(port) > 1023) and (int(port) < 65536)):
		port = input("Port to use (1024-65535) ? ")
	port = int(port)
	
	#  logging initialization
	logger = logging.getLogger("test")
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
	handler.setLevel(logging.DEBUG)
	logger.addHandler(handler)
	
	# Initialize the queue
	call_queue = queue.Queue()
	
	# Initialize the stopping event
	stop_event = threading.Event()
	
	# Server or client ?
	sercli = ""
	while sercli.lower() not in ("s", "c"):
		sercli = input("Server or client (s/c) ? ")
	
	# Server
	if sercli.lower() == "s":
		print("")
		print("***********************************************************")
		print("*                     Server side                         *")
		print("***********************************************************")
		print("")
		check_period = "check_period"
		while not (check_period.isdigit() and (int(check_period) > 0)):
			check_period = input("Period, in seconds, for checking whether remote clients are still alive ? ")
		check_period = int(check_period)
		print("")
		
		# Start the server
		server_thread = threading.Thread(target=execute_UDP_server, kwargs={"call_queue":call_queue, "stop_event":stop_event, "port":port, "check_period":check_period, "autostart":True, "logger":logger})
		server_thread.start()
		
		# loop indefinitely (unless interupted)
		try:
			print("Server is processing endlessly. Stop it with CTRL-C.")
			while True:
				time.sleep(1)
		except KeyboardInterrupt:
			print("Server is stopping...", end="", flush=True)
			stop_event.set()
			server_thread.join()
			print("stopped")
	
	# Client
	else:
		print("")
		print("***********************************************************")
		print("*                     Client side                         *")
		print("***********************************************************")
		print("")
		
		# Define the server port
		server_port = "server_port"
		while not (server_port.isdigit() and (int(server_port) > 1023) and (int(server_port) < 65536)):
			server_port = input("Unusable server port to use (1024-65535) ? ")
		server_port = int(server_port)
		
		# Create a Player
		print("Create a player")
		name = input("Name of the player ? ")
		color = "xx"
		while color[0].lower() not in ("w", "b"):
			color = input("Color of the player (w for white, b for black) ? ")
		color = chess.WHITE if color[0].lower() == "w" else chess.BLACK
		player = domichess.game.Player(name=name, color=color)
		
		# Start the thread with an unstarted server
		server_thread = threading.Thread(target=execute_UDP_server, kwargs={"call_queue":call_queue, "stop_event":stop_event, "port":port, "check_period":1, "server_port":server_port, "autostart":False, "logger":logger})
		server_thread.start()
		
		# Retrieve usefull attributes
		started = call_queue.get()
		local_address = call_queue.get()
		play_addr = call_queue.get()
		
		# Retrieve usefull methods
		start = call_queue.get()
		find_remote_players = call_queue.get()
		check_remote_players = call_queue.get()
		send_player_characteristics = call_queue.get()
		send_player_update = call_queue.get()
		
		# Inform the other players over the LAN that I exist !
		# Unnecessary since a serve is running elsewhere on the same host
		# find_remote_players()
		
		# Addresses of the other available players
		addresses = list()
		addr = "fake"
		while addr:
			addr = input("IPv4 address of a remote player (leave empty when finished) ? ")
			if addr:
				addresses.append(addr)
		
		# Fill the remote address players list
		for addr in addresses:
			play_addr.append(addr)
		
		# Send the characteristics to all other players on the LAN
		input("Press RETURN when ready to send the characteristics to all other players")
		send_player_characteristics(player)
		
		# Switch the color
		yesno = "xx"
		while yesno[0].lower() not in ("y", "n"):
			yesno = input("Do you want to switch the color of the current player (y/n) ?")
		if yesno[0].lower() == "y":
			send_player_update(domichess.network.opcode.PLAYERCOLOR, not color)
		
		# Change the name
		yesno = "xx"
		while yesno[0].lower() not in ("y", "n"):
			yesno = input("Do you want to change the name of the current player (y/n) ?")
		if yesno[0].lower() == "y":
			name = input("New name of the player ? ")
			send_player_update(domichess.network.opcode.PLAYERNAME, name)
		
		# Finish
		input("Press RETURN when ready to stop the client")
		stop_event.set()
		server_thread.join()

# Main program,
# running only if the module is NOT imported (but directly executed)
#-------------------------------------------------------------------
if __name__ == '__main__':
	main()
	