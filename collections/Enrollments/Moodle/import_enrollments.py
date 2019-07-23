#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.2"
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

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/import_enrollments.log', level=logging.INFO)


parser = OpenLRW.parser
parser.add_argument('-f', '--from', required='True', action='store', help='Timestamp (FROM) for querying Moodle`s database')
args = vars(OpenLRW.enable_argparse())


# -------------- GLOBAL --------------
TIMESTAMP_REGEX = r'^(\d{10})?$'
DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']


# -------------- FUNCTIONS --------------

def exit_log(enrollment_id, reason):
    """
    Stops the script and email + logs the last event
    :param enrollment_id:
    :param reason:
    """

    message = "An error occured when sending the object " + str(enrollment_id) + "\n\n Details: \n" + str(reason)
    db.close()
    OpenLrw.mail_server("Error Moodle Enrollments", message)
    logging.error(message)
    OpenLRW.pretty_error("HTTP POST Error", "Cannot send the enrollment object " + str(enrollment_id))
    sys.exit(0)


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

# ----- MAIN -------

if not re.match(TIMESTAMP_REGEX, args['from']):
    OpenLRW.pretty_error("Wrong usage", ["Argument must be a timestamp (from)"])

query.execute("SELECT assignment.id, user.username, context.instanceid, assignment.userid, assignment.roleid  "
              "FROM mdl_role_assignments as assignment, mdl_context as context, mdl_user as user "
              "WHERE context.id = assignment.contextid "
              "AND user.id = assignment.userid AND (assignment.roleid = 3 OR assignment.roleid = 4 OR assignment.roleid = 5)"
              "AND assignment.timemodified >= " + args['fr'])

enrollments = query.fetchall()

JWT = OpenLrw.generate_jwt()

OpenLRW.pretty_message('Info', 'Executing...')

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
        time.sleep(0.01)
        OpenLrw.post_enrollment(class_id, json, JWT, True)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_enrollment(class_id, json, JWT, True)
    except InternalServerErrorException:
        exit_log(enrollment_id, "Error 500")
    except requests.exceptions.ConnectionError as e:
        time.sleep(0.5)
        try:  # last try
            OpenLrw.post_enrollment(class_id, json, JWT, True)
        except requests.exceptions.ConnectionError as e:
            exit_log(enrollment_id, e)

db.close()

OpenLRW.pretty_message("Script finished", "Total number of enrollments sent : " + str(len(enrollments)))

message = "import_enrollments.py finished its execution in " + measure_time() + " seconds " \
          "\n\n -------------- \n SUMMARY \n -------------- \n Total number of enrollments sent : "\
          + str(len(enrollments))

OpenLrw.mail_server("Subject: Moodle Enrollments script finished", message)
logging.info("Script finished | Total number of enrollments sent : " + str(len(enrollments)))