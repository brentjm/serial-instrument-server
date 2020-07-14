#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Brent Maranzano"
__license__ = "MIT"

"""
Module to create a socket server that accepts multiple connections to service
clients attempting to communicate with underlying instruments. The server expects
messages to follow format defined in libserver.py.
"""

import sys
import socket
import selectors
import traceback
import argparse
import logging
import logging.config
import yaml
import coloredlogs
from pdb import set_trace

import libserver

logger = logging.getLogger(__name__)

def setup_logger(config_file="./logger_conf.yml"):
	try:
		with open(config_file, 'rt') as file_obj:
			config = yaml.safe_load(file_obj.read())
			logging.config.dictConfig(config)
			coloredlogs.install()
	except Exception as e:
		print(e)
		logging.basicConfig(level=default_level)
		coloredlogs.install(level=default_level)


class SocketServer(object):
    """Socket server.
    Based off of code from:
    https://github.com/realpython/materials/blob/master/python-sockets-tutorial/libclient.py
    https://realpython.com/python-sockets/
    """
    def __init__(self, host, port):
        self._lsock, self._sel = self._setup_socket(host, port)
        self.run()

    def _setup_socket(self, host, port):
        """Setup the starting socket to listen for connections.
        """
        sel = selectors.DefaultSelector()

        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((host, port))
        lsock.listen()
        print("listening on", (host, port))
        lsock.setblocking(False)
        sel.register(lsock, selectors.EVENT_READ, data=None)
        return lsock, sel

    def _accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print("accepted connection from", addr)
        conn.setblocking(False)
        message = libserver.Message(self._sel, conn, addr)
        self._sel.register(conn, selectors.EVENT_READ, data=message)

    def run(self):
        try:
            while True:
                events = self._sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self._accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            print(
                                "main: error: exception for",
                                f"{message.addr}:\n{traceback.format_exc()}",
                            )
                            message.close()
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self._sel.close()

if __name__ == "__main__":
    setup_logger()
    parser = argparse.ArgumentParser(description="Start a socker server")
    parser.add_argument(
        "--host",
        help="host address for the socket to bind",
        type=str,
        default="127.0.0.1"
    )
    parser.add_argument(
        "--port",
        help="port number for the socket server",
        type=int,
        default=5007
    )
    args = parser.parse_args()
    socket_server = SocketServer(args.host, args.port)
