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
import sys
import time

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

def execute_UDP_server(port:int, check_period:int):
	"""
	Executes endlessely the UDP server.
	
	Blocks until interrupted: this function should be called in a separated thread.
	"""
	

# Main function
#--------------
def main():
	""" Main program execution"""
	
	print("***********************************************************")
	print("*                     Network Test n°1                    *")
	print("*                                                         *")
	print("*     Test the finding player management over the LAN     *")
	print("***********************************************************")
	print("")
	port = "port"
	while not (port.isdigit() and (int(port) > 1023) and (int(port) < 65536)):
		port = input("Port to use (1024-65535) ? ")
	port = int(port)
	check_period = "check_period"
	while not (check_period.isdigit() and (int(check_period) > 0)):
		check_period = input("Period, in seconds, for checking whether remote clients are still alive ? ")
	check_period = int(check_period)
	print("")
	
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
	
	# Start the server
	finder_server = domichess.network.LANFinderServer(port = port, logger = logger)
	finder_server.start()
	
	# loop indefinitely (unless interupted)
	try:
		print("Server is processing endlessly. Stop it with CTRL-C.")
		while True:
			time.sleep(check_period)
			finder_server.check_remote_players()
	except KeyboardInterrupt:
		print("Server is stopping...", end="", flush=True)
		finder_server.shutdown()
		print("stopped")

# Main program,
# running only if the module is NOT imported (but directly executed)
#-------------------------------------------------------------------
if __name__ == '__main__':
	main()
	