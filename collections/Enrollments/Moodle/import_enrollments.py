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

logging.basicConfig(filename=os.path.dirname(__file__) + '/import_enrollments.log', level=logging.ERROR)

# -------------- GLOBAL --------------
DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']

URI = SETTINGS['api']['uri'] + '/api/classes/'

MAIL = None


# -------------- FUNCTIONS --------------
def post_enrollment(jwt, class_id, data):
    response = requests.post(URI + str(class_id) + '/enrollments?check=false', headers={'Authorization': 'Bearer ' + jwt}, json=data)
    print(Colors.OKBLUE + '[POST]' + Colors.ENDC + '/classes/' + str(class_id) + '/enrollments - Response: ' + str(response.status_code))
    return response.status_code


def exit_log(enrollment_id, reason):
    """
    Stops the script and email + logs the last event
    :param enrollment_id:
    :param reason:
    """
    result_id = str(enrollment_id)
    reason = str(reason)

    MAIL = smtplib.SMTP('localhost')
    email_message = "Subject: Error Moodle Enrollments \n\n An error occured when sending the object " + enrollment_id + \
                    "\n\n Details: \n" + reason
    db.close()
    MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], email_message)
    logging.error("Subject: Error Moodle Enrollments \n\n An error occured when sending the object " + enrollment_id + \
                  "\n\n Details: \n" + reason)
    pretty_error("Error on POST", "Cannot send the enrollment object " + result_id)  # It will also exit
    sys.exit(0)


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

query.execute("SELECT assignment.id, assignment.userid "
              "FROM mdl_role_assignments as assignment, mdl_context as context "
              "WHERE context.id = assignment.contextid "
              "AND assignment.roleid = 5")

enrollments = query.fetchall()

JWT = generate_jwt()

for enrollment in enrollments:
    enrollment_id, user_id = enrollment[0], enrollment[1]
    json = {
        'sourcedId': enrollment_id,
        'role': 'student',
        'user': {
            'sourcedId': user_id,
        },
        'primary': True,
        'status': 'active'
    }

    try:
        response = post_enrollment(JWT, enrollment_id, json)
        if response == 401:
            JWT = generate_jwt
            post_enrollment(JWT, enrollment_id, json)
        elif response == 500:
            exit_log(enrollment_id, "Error 500")
    except requests.exceptions.ConnectionError as e:
        exit_log(enrollment_id, e)

db.close()

pretty_message("Script finished",
               "Total number of enrollments sent : " + str(len(enrollments)))

MAIL = smtplib.SMTP('localhost')

MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], "Subject: Moodle Enrollments script finished \n\n "
                                                                  "import_enrollments.py finished its execution \n\n -------------- \n SUMMARY \n -------------- \n" +
              "Total number of enrollments sent : " + str(len(enrollments)))