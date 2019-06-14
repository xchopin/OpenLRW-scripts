#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb
import sys
import os
import requests
import datetime

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/import_lineitems.log', level=logging.ERROR)

# -------------- GLOBAL --------------
DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']

COUNTER = 0


def exit_log(lineitem_id, reason):
    """
    Stops the script and email + logs the last event
    :param lineitem_id:
    :param reason:
    """

    message = "Error Moodle line item \n\n An error occured when sending the line item " + str(lineitem_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(" Error Moodle line item", message)
    logging.error(message)
    OpenLrw.pretty_error("Error on POST", "Cannot send the line item object " + str(lineitem_id))
    sys.exit(0)


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

query.execute("SELECT id, course, name, intro, timeopen, timeclose FROM mdl_quiz")

line_items = query.fetchall()

JWT = OpenLrw.generate_jwt()

for line_item in line_items:
    quiz_id, class_id, name, description, open_date, close_date = line_item
    open_date = datetime.datetime.fromtimestamp(open_date).strftime('%Y-%m-%dT%H:%M:%S.755Z') if open_date > 0 else None
    close_date = datetime.datetime.fromtimestamp(close_date).strftime('%Y-%m-%dT%H:%M:%S.755Z') if close_date > 0 else None

    json = {
        "sourcedId": "quiz_" + str(quiz_id),
        "title": name,
        "description": description,
        "assignDate": open_date,
        "dueDate": close_date,
        "class": {
            "type": "quiz",
            "sourcedId": str(class_id)
        }
    }

    try:
        res = OpenLrw.post_lineitem_for_a_class(class_id, json, JWT, True)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_lineitem_for_a_class(class_id, json, JWT, True)
    except BadRequestException as e:
        exit_log(quiz_id, e.message.content)
    except InternalServerErrorException:
        exit_log(quiz_id, "Internal Server Error 500")
    except requests.exceptions.ConnectionError as e:
        exit_log(quiz_id, e)

COUNTER = len(line_items)


line_items = {}  # Clears buffer

# Active quiz
query.execute("SELECT id, course, name, intro, scale FROM mdl_activequiz")

line_items = query.fetchall()

for line_item in line_items:
    quiz_id, class_id, name, description, scale = line_item
    json = {
        "sourcedId": "active_quiz_" + str(quiz_id),
        "title": name,
        "description": description,
        "class": {
            "sourcedId": class_id
        },
        "metadata": {
            "type": "activequiz",
            "resultValueMax": str(scale)
        }
    }

    try:
        OpenLrw.post_lineitem_for_a_class(class_id, json, JWT, True)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_lineitem_for_a_class(class_id, json, JWT, True)
    except BadRequestException as e:
        exit_log(quiz_id, e.message.content)
    except InternalServerErrorException:
        exit_log(quiz_id, "Internal Server Error 500")
    except requests.exceptions.ConnectionError as e:
        exit_log(quiz_id, e)


COUNTER = COUNTER + len(line_items)
db.close()

OpenLRW.pretty_message("Script finished", "Total number of line items sent : " + str(COUNTER))

message = str(sys.argv[0]) + " finished its execution in " + measure_time() + " seconds\n\n -------------- \n SUMMARY \n -------------- \n" + "Total number of line items sent : " + str(COUNTER)

OpenLrw.mail_server(str(sys.argv[0] + " executed"), message)
logging.info(message)
