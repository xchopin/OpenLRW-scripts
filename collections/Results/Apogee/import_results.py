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
import json

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/import_results.log', level=logging.ERROR)

# -------------- GLOBAL --------------
URI = SETTINGS['api']['uri'] + '/api'
RESULT_COUNTER = 0
LINEITEM_COUNTER = 0
MAIL = None
FILE_NAME = 'data/Results/Notes_IC0_2018.csv'
RESULT_NAMES = 'data/Results/name.csv'


def exit_log(result_id, reason):
    """
    Stops the script and email + logs the last event
    :param result_id:
    :param reason:
    """
    subject = "Error Apogée Results"
    message = "An error occured when sending the result " + str(result_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(subject, message)
    logging.error(message)
    OpenLrw.pretty_error("Error on POST", "Cannot send the result object " + str(result_id))
    sys.exit(0)


# -------------- MAIN --------------
OpenLRW.pretty_message("CSV Files used for the import", FILE_NAME + " | " + RESULT_NAMES)

JWT = OpenLrw.generate_jwt()
line_items = json.loads(OpenLrw.get_lineitems(JWT))

# Create a temporary class
try:
    response = requests.post(URI, headers={'Authorization': 'Bearer ' + JWT}, json={'sourcedId': 'unknown_apogee', 'title': 'Apogée temporaire'})
    if response == 500:
        exit_log('Unable to create the Class "Apogée"', response)
except requests.exceptions.ConnectionError as e:
    exit_log('Unable to create the Class "Apogée"', e)

f1 = open(FILE_NAME, 'r')

mapping = list(csv.reader(open(RESULT_NAMES, "rb"), delimiter=';'))
# - - - - PARSING THE CSV FILE - - - -
with f1:
        c1 = csv.reader(f1, delimiter=";")
        for row in c1:
            username, year, degree_id, degree_version, inscription, term_id, term_version = row[0], row[1], row[2], row[3], row[4], row[5], row[6]

            for x in range(7, len(row)):  # grades
                data = row[x].split('-')
                grade = {'type': data[0], 'exam_id': data[1], 'score': data[2], 'status': None}
                if len(data) > 3:
                    grade['status'] = data[3]

                json = {
                    'sourcedId': str(uuid.uuid4()),
                    'score': str(grade['score']),
                    'resultStatus': grade['status'],
                    'student': {
                        'sourcedId': username
                    },
                    'lineitem': {
                        'sourcedId': grade['exam_id']
                    },
                    'metadata': {
                        'type': grade['type'],
                        'year': year,
                        'category': 'Apogée'
                    }
                }

                # Let's send the result object
                RESULT_COUNTER = RESULT_COUNTER + 1

                try:
                    OpenLrw.post_result_for_a_class('unknown_apogee', json, JWT, False)  # It makes no sense to check since it's a random sourcedId
                except ExpiredTokenException:
                    JWT = OpenLrw.generate_jwt()
                    OpenLrw.post_result_for_a_class('unknown_apogee', json, JWT, False)
                except BadRequestException as e:
                    exit_log(grade['exam_id'], e.message.content)
                except InternalServerErrorException as e:
                    exit_log(grade['exam_id'], e.message.content)
                except requests.exceptions.ConnectionError as e:
                    exit_log('Unable to create the Class "Apogée"', e)

                # Does the lineItem exist?
                res = False

                for i in range(0, len(line_items)):
                    if line_items[i]['lineItem']['sourcedId'] == grade['exam_id']:
                        res = True
                        break

                # If it does not we will create it
                if not res:

                    title = "null"
                    for line in mapping:
                        code_elp, name, etp = line
                        if code_elp == grade['exam_id']:
                            title = name

                    item = {
                        "sourcedId": grade['exam_id'],
                        "lineItem": {
                            "sourcedId": grade['exam_id']
                        },
                        "title": title,
                        "description": "null",
                        "assignDate": "",
                        "dueDate": "",
                        "class": {
                            "sourcedId": "unknown_apogee"
                        }
                    }

                    # Add new line item to the dynamic array
                    line_items.append(item)
                    LINEITEM_COUNTER = LINEITEM_COUNTER + 1
                    try:
                        OpenLrw.post_lineitem(item, JWT, False)
                    except ExpiredTokenException:
                        JWT = OpenLrw.generate_jwt()
                        OpenLrw.post_lineitem(item, JWT, False)
                    except InternalServerErrorException:
                        exit_log(grade['exam_id'], response)
                    except requests.exceptions.ConnectionError as e:
                        exit_log('Unable to create the LineItem ' + grade['exam_id'], e)


OpenLrw.pretty_message("Script finished", "Results sent: " + str(RESULT_COUNTER) + " - LineItems sent: " + str(LINEITEM_COUNTER))
message = "import_results.py finished its execution in " + measure_time() + " seconds \n\n -------------- \n SUMMARY \n -------------- \n" \
          + " Results sent : " + str(RESULT_COUNTER) + " - LineItems sent : " + str(LINEITEM_COUNTER)
OpenLrw.mail_server(sys.argv[0] + " executed", message)


