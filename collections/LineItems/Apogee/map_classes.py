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
URI = SETTINGS['api']['uri'] + '/api'
ROWS_NUMBER = 0
MAIL = None
FILE_NAME = 'data/mapping.csv'


# -------------- FUNCTIONS --------------

def get_lineitems(jwt):
    response = requests.get(URI + '/lineitems', headers={'Authorization': 'Bearer ' + jwt})
    print(Colors.OKGREEN + '[GET]' + Colors.ENDC + '/lineitems - Response: ' + str(response.status_code))
    return response


def create_lineitem(jwt, data):
    response = requests.post(URI + '/lineitems', headers={'Authorization': 'Bearer ' + jwt}, json=data)
    print(Colors.OKBLUE + '[POST]' + Colors.ENDC + '/lineitems - Response: ' + str(response.status_code))
    return response


def exit_log(result_id, reason):
    """
    Stops the script and email + logs the last event
    :param result_id:
    :param reason:
    """
    result_id = str(result_id)
    reason = str(reason)

    MAIL = smtplib.SMTP('localhost')
    email_message = "Subject: Error Apogée Results \n\n An error occured when sending the result " + result_id + "\n\n Details: \n" + reason

    MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], email_message)
    logging.error(
        "Subject: Error Apogée Results \n\n An error occured when sending the result " + result_id + "\n\n Details: \n" + reason)
    pretty_error("Error on POST", "Cannot send the result object " + result_id)
    sys.exit(0)


# -------------- MAIN --------------

JWT = generate_jwt()

line_items = get_lineitems(JWT).json()

# Creates a class for Apogee (temporary)
try:
    response = requests.post(URI, headers={'Authorization': 'Bearer ' + JWT},
                             json={'sourcedId': 'unknown_apogee', 'title': 'Apogée'})
    if response == 500:
        exit_log('Unable to create the Class "Apogée"', response)
except requests.exceptions.ConnectionError as e:
    exit_log('Unable to create the Class "Apogée"', e)

f = open(FILE_NAME, 'r')

# - - - - PARSING THE CSV FILE - - - -
with f:
    reader = csv.reader(f, delimiter=";")
    ROWS_NUMBER = sum(1 for line in open(FILE_NAME))
    for row in reader:
        username, year, degree_id, degree_version, inscription, term_id, term_version = row[0], row[1], row[2], row[3], \
                                                                                        row[4], row[5], row[6]

pretty_message("Script finished", "Total number of results sent : " + str(ROWS_NUMBER))

MAIL = smtplib.SMTP('localhost')

MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], "Subject: Apogée Results script finished \n\n "
                                                                  "import_results.py finished its execution in " + measure_time() +
              " seconds \n\n -------------- \n SUMMARY \n -------------- \n" +
              "Total number of results sent : " + str(ROWS_NUMBER))

