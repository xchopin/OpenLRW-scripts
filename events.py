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

# -------------- GLOBAL --------------
HOST = settings.logstash['host']
PORT = settings.logstash['port']


# -------------- FUNCTIONS --------------
def post_event(jwt, data):
    response = requests.post(settings.api['uri'] + '/events', headers={'Authorization': 'Bearer ' + jwt}, json=data)
    return response.status_code != 401  # if token expired


def parse_json_stream(stream):
    decoder = json.JSONDecoder()
    while stream:
        obj, idx = decoder.raw_decode(stream)
        yield obj
        stream = stream[idx:].lstrip()


# -------------- TCP SERVER --------------
class SingleTCPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        while True:
            try:
                data = self.request.recv(1024)  # 1Kb input
            except SocketError as e:
                if e.errno != errno.ECONNRESET:
                    raise
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


# -------------- MAIN --------------
if __name__ == "__main__":
    server = SimpleServer((HOST, PORT), SingleTCPHandler)
    pretty_message('Starting TCP Server on ' + HOST + ':' + str(PORT), 'Listener enabled, waiting for Logstash events')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
