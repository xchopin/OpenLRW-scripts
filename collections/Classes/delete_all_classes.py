#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.3"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import sys
import os
import requests

sys.path.append(os.path.dirname(__file__) + '/../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/delete_all_classes.log', level=logging.ERROR)
OpenLRW.enable_argparse()  # Otherwise it creates an error

def exit_log(reason):
    """
    Stops the script and email + logs the last event
    :param reason:
    """
    message = "An error occured when deleting the classes collection " + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(sys.argv[0], message)
    logging.error(message)
    OpenLRW.pretty_error("HTTP DELETE Error", "Cannot delete the classes collection")
    sys.exit(0)


JWT = OpenLrw.generate_jwt()

try:
    OpenLrw.delete_classes(JWT)
except InternalServerErrorException as e:
    exit_log(e.message.content)
except requests.exceptions.ConnectionError as e:
    exit_log(e)


OpenLRW.pretty_message("Script finished", "Class collection deleted")


OpenLrw.mail_server(sys.argv[0], "Class collection deleted")
logging.info("Collection deleted")
