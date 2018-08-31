#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb
import datetime
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

URI = SETTINGS['api']['uri'] + '/api/classes/'

MAIL = None


# -------------- FUNCTIONS --------------
def post_lineitem(jwt, class_id, data):
    response = requests.post(URI + str(class_id) + '/lineitems?check=false', headers={'Authorization': 'Bearer ' + jwt}, json=data)
    print(Colors.OKBLUE + '[POST]' + Colors.ENDC + '/classes/' + str(class_id) + '/lineitems - Response: ' + str(response.status_code))
    return response.status_code


def exit_log(lineitem_id, reason):
    """
    Stops the script and email + logs the last event
    :param lineitem_id:
    :param reason:
    """
    lineitem_id = str(lineitem_id)
    reason = str(reason)

    MAIL = smtplib.SMTP('localhost')
    email_message = "Subject: Error Moodle line item \n\n An error occured when sending the line item " + lineitem_id + \
                    "\n\n Details: \n" + reason
    db.close()
    MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], email_message)
    logging.error("Subject: Error Moodle line item \n\n An error occured when sending the line item" + lineitem_id + \
                  "\n\n Details: \n" + reason)
    pretty_error("Error on POST", "Cannot send the line item object " + lineitem_id)  # It will also exit
    sys.exit(0)


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

query.execute("SELECT id, course, name, intro, timeopen, timeclose FROM mdl_quiz")

line_items = query.fetchall()

JWT = generate_jwt()

for line_item in line_items:
    quiz_id, class_id, name, description, open_date, close_date = line_item
    open_date = datetime.datetime.fromtimestamp(open_date).strftime('%Y-%m-%dT%H:%M:%S') if open_date > 0 else None
    close_date = datetime.datetime.fromtimestamp(close_date).strftime('%Y-%m-%dT%H:%M:%S') if close_date > 0 else None

    json = {
        "sourcedId": quiz_id,
        "title": name,
        "description": description,
        "assignDate": open_date,
        "dueDate": close_date,
        "class": {
            "sourcedId": class_id
        }
    }

    try:
        response = post_lineitem(JWT, class_id, json)
        if response == 401:
            JWT = generate_jwt()
            post_lineitem(JWT, class_id, json)
        elif response == 500:
            exit_log(quiz_id, response)
    except requests.exceptions.ConnectionError as e:
        exit_log(quiz_id, e)

db.close()

pretty_message("Script finished",
               "Total number of line items sent : " + str(len(line_items)))

MAIL = smtplib.SMTP('localhost')

MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'],
              "Subject: Moodle line item script finished \n\n import_lineitems.py finished its execution in "
              + measure_time() + " seconds\n\n -------------- \n SUMMARY \n -------------- \n" +
              "Total number of line items sent : " + str(len(line_items)))

