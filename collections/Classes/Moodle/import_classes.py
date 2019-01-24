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
import re
import requests

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/import_classes.log', level=logging.ERROR)

# -------------- GLOBAL --------------
DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']

URI = SETTINGS['api']['uri'] + '/api/classes'

MAIL = None
FILE_PATH = './data/active_classes.txt'


# -------------- FUNCTIONS --------------
def post_class(jwt, data):
    response = requests.post(URI, headers={'Authorization': 'Bearer ' + jwt}, json=data)
    print(Colors.OKBLUE + '[POST]' + Colors.ENDC + ' /classes - Response: ' + str(response.status_code))
    return response.status_code


def exit_log(course_id, reason):
    """
    Stops the script and email + logs the last event
    :param course_id:
    :param reason:
    :ret
    """
    MAIL = smtplib.SMTP('localhost')
    email_message = "Subject: Error Moodle Courses \n\n An error occured when sending the course " + course_id + \
                    "\n\n Details: \n" + str(reason)
    db.close()
    MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], email_message)
    logging.error("Subject: Error Moodle Courses \n\n An error occured when sending the course " + course_id + \
                  "\n\n Details: \n" + str(reason))
    pretty_error("Error on POST", "Cannot send the course object " + course_id)  # It will also exit
    sys.exit(0)


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()


if not os.path.isfile(FILE_PATH):
    pretty_error(FILE_PATH + " does not exist", "You have to create it following the documentation.")
    exit()

active_classes = []
f = open(FILE_PATH, "r")
print("Parsing the file...")

for line in f:
    if line.startswith('#') or line.startswith(' '):
        continue
    content = re.search(r'\d+', line)
    if content:  # solve issues for lines with only characters
        active_classes.append(content.group())

# Query to get a population (BALI)
query.execute("SELECT instanceid, valeur FROM mdl_enrol_bali, mdl_context " +
              "WHERE mdl_context.id = mdl_enrol_bali.contextid AND contextlevel = 50 AND type = 'FORM' ")

results = query.fetchall()
population = dict()
for result in results:
    if result[0] in population:  # If this key already exists it concatenates
        population[result[0]] += "|" + str(result[1])
    else:
        population[result[0]] = result[1]

# Query to get all the visible courses
query.execute("SELECT id, idnumber, fullname, timemodified, summary FROM mdl_course WHERE visible = 1")

JWT = generate_jwt()

courses = query.fetchall()

for course in courses:
    course_id, identifier, title, last_modified, summary = course
    json = {
        'sourcedId': course_id,
        'title': title,
        'status': 'active' if course_id in active_classes else 'inactive',
        'metadata': {
            'summary': summary,
            'lastModified': last_modified,
            'classCode': identifier if identifier != '' else None,
            'populationBali': population[course_id] if course_id in population else None
        }
    }

    response = post_class(JWT, json)

    if response == 401:
        JWT = generate_jwt()
        post_class(JWT, json)
    elif response == 500:
        exit_log(course_id, response)

db.close()

pretty_message("Script finished",
               "Total number of courses sent : " + str(len(courses)))

MAIL = smtplib.SMTP('localhost')

MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], "Subject: Moodle Courses script finished \n\n "
              "import_classes.py finished its execution in " + measure_time() + " seconds"
              " \n\n -------------- \n SUMMARY \n -------------- \n" + "Total number of courses sent : " + str(len(courses)))
