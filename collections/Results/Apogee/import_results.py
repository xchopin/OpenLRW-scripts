#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.1.2"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import hashlib
import sys
import os
import requests
import csv
import json

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/import_results.log', level=logging.INFO)

# -------------- GLOBAL --------------
URI = SETTINGS['api']['uri'] + '/api'
RESULT_COUNTER = 0
LINEITEM_COUNTER = 0
MAIL = None
RESULT_NAMES = SETTINGS['apogee']['lineitems_name_filepath']

if RESULT_NAMES is None or RESULT_NAMES == "":
    OpenLrw.pretty_error("Settings parameter not filled", "'lineitems_name_filepath' parameter from settings.yml is empty")

if len(sys.argv) < 2:
    OpenLRW.pretty_error("Missing argument", ["A filepath is required to access to the Apogee results (.csv file) "])
    sys.exit(0)
else:
    FILE_NAME = sys.argv[1]


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

                    string = str(username) + str(grade['exam_id']) + str(grade['score'] + str(year))
                    sourcedId = hashlib.sha1(string)
                    json = {
                        'sourcedId': str(sourcedId.hexdigest()),
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
                        OpenLrw.post_result_for_a_class('unknown_apogee', json, JWT, True)
                    except ExpiredTokenException:
                        JWT = OpenLrw.generate_jwt()
                        OpenLrw.post_result_for_a_class('unknown_apogee', json, JWT, True)
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

                    # If it doesn't we will create it
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
                            OpenLrw.post_lineitem(item, JWT, True)  # We check since the line item can already exist
                        except ExpiredTokenException:
                            JWT = OpenLrw.generate_jwt()
                            OpenLrw.post_lineitem(item, JWT, True)
                        except InternalServerErrorException as e:
                            exit_log(grade['exam_id'], e.message.content)
                        except requests.exceptions.ConnectionError as e:
                            exit_log('Unable to create the LineItem ' + grade['exam_id'], e)

OpenLrw.pretty_message("Script finished", "Results sent: " + str(RESULT_COUNTER) + " - LineItems sent: " + str(LINEITEM_COUNTER))
message = "Script executed in " + measure_time() + " seconds \n\n -------------- \n SUMMARY \n -------------- \n" \
          + str(RESULT_COUNTER) + " results sent \n " + str(LINEITEM_COUNTER) + " lineItems sent"
OpenLrw.mail_server(sys.argv[0] + " executed", message)
logging.info(message)

