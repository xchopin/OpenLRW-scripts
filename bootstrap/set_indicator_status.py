#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.3"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import os
import sys
import requests

from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/maintenance_mode.log', level=logging.ERROR)


def exit_log(reason):
    """
    Stop the script and email + log
    :param reason:
    """

    message = "An error occurred when changing the server status: " + str(reason)
    OpenLrw.mail_server(sys.argv[0] + " Error", message)
    logging.error(message)
    OpenLRW.pretty_error("HTTP POST Error", "An error occurred when changing the server status")
    sys.exit(0)


status = ''

if len(sys.argv) == 2:
    if sys.argv[1].upper() == 'MAINTENANCE':
        status = 'MAINTENANCE'
    elif sys.argv[1].upper() == 'UP':
        status = 'UP'
    elif sys.argv[1].upper() == 'DOWN':
        status = 'DOWN'
    else:
        OpenLRW.pretty_error("Wrong usage", ["Only MAINTENANCE, UP and DOWN are accepted as a status"])
else:
    OpenLRW.pretty_error("Wrong usage", ["This script requires a string argument"])

OpenLrw.generate_jwt()

try:
    OpenLrw.change_indicator()
except BadRequestException as e:
    exit_log(e.message.content)
except InternalServerErrorException as e:
    exit_log(e.message.content)
except requests.exceptions.ConnectionError as e:
    exit_log(e)

OpenLrw.mail_server(sys.argv[0], 'Indicator status has been set to ' + sys.argv[1])
