#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import datetime
import sys
import os
import requests
import datetime
import csv
import uuid

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/map_classes.log', level=logging.ERROR)



# -------------- GLOBAL --------------
ROWS_NUMBER = 0
FILE_NAME = 'data/mapping.csv'


def exit_log(result_id, reason):
    """
    Stops the script and email + logs the last event
    :param result_id:
    :param reason:
    """
    message = "An error occured when sending the result " + str(result_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(" Error Apogee Results", message)
    logging.error(message)
    OpenLrw.pretty_error("Error on POST", "Cannot send the result object " + str(result_id))
    sys.exit(0)


# -------------- MAIN --------------

JWT = OpenLrw.generate_jwt()

line_items = OpenLrw.get_lineitems(JWT)

# Creates a class for Apogee (temporary)
try:
    OpenLrw.post_class({'sourcedId': 'unknown_apogee', 'title': 'Apogée'}, JWT, False)
except InternalServerErrorException:
        exit_log('Unable to create the Class "Apogee"', "Internal Server Error 500")
except requests.exceptions.ConnectionError as e:
    exit_log('Unable to create the Class "Apogee"', e)

f = open(FILE_NAME, 'r')

# - - - - PARSING THE CSV FILE - - - -
with f:
    reader = csv.reader(f, delimiter=";")
    ROWS_NUMBER = sum(1 for line in open(FILE_NAME))
    for row in reader:
        username, year, degree_id, degree_version, inscription, term_id, term_version = row[0], row[1], row[2], row[3], \
                                                                                        row[4], row[5], row[6]

OpenLrw.pretty_message("Script finished", "Total number of results sent : " + str(ROWS_NUMBER))

message = "import_results.py finished its execution in " + measure_time() + " seconds \n\n -------------- \n SUMMARY \n -------------- \n" + "Total number of results sent : " + str(ROWS_NUMBER)

OpenLrw.mail_server("Apogee Results script finished", message)
