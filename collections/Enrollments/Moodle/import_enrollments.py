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
import re

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/import_enrollments.log', level=logging.ERROR)

# -------------- GLOBAL --------------
TIMESTAMP_REGEX = r'^(\d{10})?$'
DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']

URI = SETTINGS['api']['uri'] + '/api/classes/'

MAIL = None


# -------------- FUNCTIONS --------------
def post_enrollment(jwt, class_id, data):
    response = requests.post(URI + str(class_id) + '/enrollments?check=false',
                             headers={'Authorization': 'Bearer ' + jwt}, json=data)
    print(Colors.OKBLUE + '[POST]' + Colors.ENDC + '/classes/' + str(class_id) + '/enrollments - Response: ' + str(
        response.status_code))
    return response.status_code


def exit_log(enrollment_id, reason):
    """
    Stops the script and email + logs the last event
    :param enrollment_id:
    :param reason:
    """
    enrollment_id = str(enrollment_id)
    reason = str(reason)

    MAIL = smtplib.SMTP('localhost')
    email_message = "Subject: Error Moodle Enrollments \n\n An error occured when sending the object " + enrollment_id + \
                    "\n\n Details: \n" + reason
    db.close()
    MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], email_message)
    logging.error("Subject: Error Moodle Enrollments \n\n An error occured when sending the object " + enrollment_id + \
                  "\n\n Details: \n" + reason)
    pretty_error("Error on POST", "Cannot send the enrollment object " + enrollment_id)  # It will also exit
    sys.exit(0)


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

# ----- MAIN -------
if not (len(sys.argv) > 1):
    pretty_error("Wrong usage", ["This script requires at least 1 timestamp argument (from)"])
else:
    if not re.match(TIMESTAMP_REGEX, sys.argv[1]):
        pretty_error("Wrong usage", ["Argument must be a timestamp (from)"])

query.execute("SELECT assignment.id, user.username, context.instanceid, assignment.userid, assignment.roleid  "
              "FROM mdl_role_assignments as assignment, mdl_context as context, mdl_user as user "
              "WHERE context.id = assignment.contextid "
              "AND user.id = assignment.userid AND (assignment.roleid = 3 OR assignment.roleid = 4 OR assignment.roleid = 5)"
              "AND assignment.timemodified >= " + sys.argv[1])

enrollments = query.fetchall()

JWT = generate_jwt()

for enrollment in enrollments:
    enrollment_id, username, class_id, user_id, role = enrollment
    json = {
        'sourcedId': enrollment_id,
        'role': 'student' if role == 5 else 'teacher',
        'user': {
            'sourcedId': username,
        },
        'primary': True,
        'status': 'active'
    }

    try:
        response = post_enrollment(JWT, class_id, json)
        if response == 401:
            JWT = generate_jwt()
            post_enrollment(JWT, class_id, json)
        elif response == 500:
            exit_log(enrollment_id, "Error 500")
        time.sleep(0.01)
    except requests.exceptions.ConnectionError as e:
        time.sleep(0.5)
        try: # last try
            response = post_enrollment(JWT, class_id, json)
        except requests.exceptions.ConnectionError as e:
            exit_log(enrollment_id, e)

db.close()

pretty_message("Script finished",
               "Total number of enrollments sent : " + str(len(enrollments)))

MAIL = smtplib.SMTP('localhost')

MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], "Subject: Moodle Enrollments script finished \n\n "
              "import_enrollments.py finished its execution in " + measure_time() + " seconds "
              "\n\n -------------- \n SUMMARY \n -------------- \n Total number of enrollments sent : " + str(len(enrollments)))