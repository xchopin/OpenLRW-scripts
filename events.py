#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import SocketServer
from socket import error as SocketError
import errno
import requests, json
from bootstrap.helpers import *
from bootstrap import settings


HOST, PORT = settings.logstash['host'], settings.logstash['port']


class SingleTCPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        while True:
            try:
                data = self.request.recv(1024)  # 1Kb input
            except SocketError as e:
                if e.errno != errno.ECONNRESET:
                    raise  # Not error we are looking for
                break
            if data == '':
                self.request.close()
                break
            print data
            if not data.startswith('PROXY'):
                self.request.sendall('answer : {}'.format(data))


class SimpleServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    daemon_threads = True   # Ctrl-C will cleanly kill all spawned threads
    allow_reuse_address = True  # faster rebinding

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)


if __name__ == "__main__":
    server = SimpleServer((HOST, PORT), SingleTCPHandler)
    pretty_message('Starting TCP Server on ' + HOST + ':' + str(PORT), 'Listener enabled, waiting for Logstash events')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


