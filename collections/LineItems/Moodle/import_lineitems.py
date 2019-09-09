#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.3"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb
import sys
import os
import requests
import datetime

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/import_lineitems.log', level=logging.INFO)
OpenLRW.enable_argparse()  # Otherwise it creates an error


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


def generate_json(sourced_id, title, description, assign_date, due_date, class_sourced_id, category, result_value_max):
    """
    Generate a JSON formatted value ready to be sent to OpenLRW
    :param sourced_id:
    :param title:
    :param description:
    :param assign_date:
    :param due_date:
    :param class_sourced_id:
    :param category:
    :param result_value_max:
    :return:
    """
    if result_value_max is None:
        result_value_max = 0.0

    return {
        "sourcedId": sourced_id,
        "title": title,
        "description": description,
        "assignDate": assign_date,
        "dueDate": due_date,
        "resultValueMax": result_value_max,
        "class": {
            "sourcedId": class_sourced_id
        },
        "metadata": {
            "type": category
        }
    }


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

query.execute("SELECT id, course, name, intro, timeopen, timeclose FROM mdl_quiz")

line_items = query.fetchall()

JWT = OpenLrw.generate_jwt()

for line_item in line_items:
    quiz_id, class_id, name, description, open_date, close_date = line_item
    open_date = str(datetime.datetime.now().utcfromtimestamp(open_date).isoformat()) + '.755Z' if open_date > 0 else None
    close_date = str(datetime.datetime.now().utcfromtimestamp(close_date).isoformat()) + '.755Z' if close_date > 0 else None
    data = generate_json("quiz_" + str(quiz_id), name, description, open_date, close_date, str(class_id), "quiz", None)

    try:
        res = OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, True)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, True)
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
    data = generate_json("active_quiz_" + str(quiz_id), name, description, None, None, class_id, "activequiz", str(scale))

    try:
        OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, True)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, True)
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
