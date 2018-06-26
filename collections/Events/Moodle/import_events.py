#!/usr/bin/python
# coding: utf-8

__author__ = "Benjamin Seclier, Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.1"
__email__ = "benjamin.seclier@univ-lorraine.fr, xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb
import datetime
import sys
import os
import requests
import re

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *
from time import gmtime, strftime

logging.basicConfig(filename=os.path.dirname(__file__) + '/import_events.log', level=logging.ERROR)

# -------------- GLOBAL --------------

TIMESTAMP_REGEX = r'^(\d{10})?$'

DB_LOG_HOST = SETTINGS['db_moodle_log']['host']
DB_LOG_NAME = SETTINGS['db_moodle_log']['name']
DB_LOG_USERNAME = SETTINGS['db_moodle_log']['username']
DB_LOG_PASSWORD = SETTINGS['db_moodle_log']['password']
DB_LOG_TABLE = SETTINGS['db_moodle_log']['log_table']

DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']
MAIL = None

COUNTER_JSON_SENT = 0
TOTAL_EVENT = 0

# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
db_log = MySQLdb.connect(DB_LOG_HOST, DB_LOG_USERNAME, DB_LOG_PASSWORD, DB_LOG_NAME)

query = db.cursor()
query_log = db_log.cursor()


# -------------- FUNCTIONS --------------
def get_module_name(module_type, module_id):
    """
    Récupère le nom d'un module (fichier, test, url, etc.) pour un type et id donné
    :param module_type:  module type
    :param module_id:  module id
    :return: module name
    """
    name = "Module supprimé de la plateforme"  # Module deleted

    query.execute("SELECT name FROM mdl_" + module_type + " WHERE id = '" + str(module_id) + "';")
    res = query.fetchone()

    if res is not None:
        name = res[0]

    return name


def get_assignment_name(assignment_id):
    """
    Récupère le nom d'un devoir pour un id donné
    :param assignment_id: assignment id
    :return: assignment name
    """
    name = "Devoir supprimé de la plateforme"  # Course deleted

    query.execute("SELECT name FROM mdl_assign, mdl_assign_submission "
                  "WHERE mdl_assign_submission.assignment = mdl_assign.id "
                  "AND mdl_assign_submission.id= " + str(assignment_id) + ";")
    res = query.fetchone()

    if res is not None:
        name = res[0]

    return name


def get_quiz_name(quiz_id):
    """
    Récupère le nom du test selon l'id de la tentative
    :param quiz_id: quiz id
    :return: quiz name
    """
    name = "Quiz supprimé de la plateforme"  # Quiz deleted

    query.execute("SELECT name FROM arche_prod.mdl_quiz,arche_prod.mdl_quiz_attempts "
                  "WHERE arche_prod.mdl_quiz.id = arche_prod.mdl_quiz_attempts.quiz "
                  "AND arche_prod.mdl_quiz_attempts.id=" + str(quiz_id) + ";")
    res = query.fetchone()

    if res is not None:
        name = res[0]

    return name


def exit_log(object_id, timestamp, reason):
    """
    Stops the script and email + logs the last event
    :param statement:
    :param object_id:
    :param timestamp:
    :ret
    """
    MAIL = smtplib.SMTP('localhost')
    email_message = "Subject: Error Moodle Events \n\n An error occured when sending the event #" + object_id +\
                    " created at " + timestamp + "\n\n Details: \n" + str(reason)
    db.close()
    db_log.close()
    MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], email_message)
    logging.error("An error occured at " + strftime("%Y-%m-%d %H:%M:%S",gmtime()) + " - Event #" + object_id +
                  " created at " + timestamp + "\n\n Details: \n" + str(reason))
    pretty_error("Error on POST",
                 "Cannot send statement for event #" + object_id + " created at " + timestamp)  # It will also exit
    sys.exit(0)


def prevent_caliper_error(statement, object_id, timestamp):
    """
    Sends Caliper statement with checking response, if it fails it stops the execution and log + email the event that failed
    :param statement:
    :param object_id:
    :param timestamp:
    :return:
    """

    try:
        response_code = send_caliper_statement(statement)
        if response_code != 200:
            exit_log(object_id, timestamp, response_code)
    except requests.exceptions.ConnectionError as e:
        exit_log(object_id, timestamp, e)

    # -------------- MAIN --------------


if not (len(sys.argv) > 1):
    pretty_error("Wrong usage", ["This script requires 1 or 2 arguments (timestamps: FROM - TO)"])
elif (len(sys.argv) == 2):
    if (re.match(TIMESTAMP_REGEX, sys.argv[1])):
        sql_where = "WHERE timecreated >= " + sys.argv[1]
    else:
        pretty_error("Wrong usage", ["Argument must be a timestamp (FROM)"])
else:
    if (re.match(TIMESTAMP_REGEX, sys.argv[1]) and re.match(TIMESTAMP_REGEX, sys.argv[2])):
        sql_where = "WHERE timecreated >= " + sys.argv[1] + " AND timecreated <= " + sys.argv[2]
    else:
        pretty_error("Wrong usage", ["Arguments must be a timestamp (FROM and TO)"])

# Création d'un dictionnaire avec les id moodle et les logins UL
query.execute("SELECT id, username FROM mdl_user WHERE deleted=0 AND username LIKE '%u';")
users = query.fetchall()
moodle_students = {}
for user in users:
    moodle_students[user[0]] = user[1]

# Création d'un dictionnaire avec les id de cours moodle et leur nom
query.execute("SELECT id, fullname FROM mdl_course;")
courses = query.fetchall()
moodle_courses = {}
for course in courses:
    moodle_courses[course[0]] = course[1]

# Query for a day | Requête pour une journée
query_log.execute(
    "SELECT userid, courseid, eventname, component, action, target, objecttable, objectid, timecreated, id "
    "FROM " + DB_LOG_TABLE + " " + sql_where)

rows_log = query_log.fetchall()

TOTAL_EVENT = len(rows_log)

for row_log in rows_log:
    row = {}  # Clears previous buffer
    row["userId"] = row_log[0]
    row["courseId"] = row_log[1]
    row["eventName"] = row_log[2]
    row["component"] = row_log[3]
    row["action"] = row_log[4]
    row["target"] = row_log[5]
    row["objecttable"] = row_log[6]
    row["objectId"] = row_log[7]
    row["timeCreated"] = row_log[8]
    row["id"] = row_log[9]

    if row["userId"] in moodle_students:  # Checks if users isn't deleted from the db
        if row["courseId"] in moodle_courses:  # Checks if the course given exists in Moodle
            course_name = moodle_courses[row["courseId"]]
        else:
            course_name = "Cours supprimé de la plateforme"

        if row["eventName"] == "\core\event\course_viewed":  # Visualisation d'un cours
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_students[row["userId"]],
                            "type": "Person"
                        },
                        "action": "Viewed",
                        "object": {
                            "id": row["courseId"],
                            "type": "CourseSection",
                            "name": course_name,
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://atom.dc.univ-lorraine.fr/scripts/collections/Events/Moodle"
            }

        elif row["target"] == "course_module" and row["action"] == "viewed":  # Visualisation d'un module de cours
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_students[row["userId"]],
                            "type": "Person"
                        },
                        "action": "Viewed",
                        "object": {
                            "id": row["objectId"],
                            "type": "DigitalResource",
                            "name": get_module_name(row["objecttable"], row["objectId"]),
                            "description": row["component"],
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://atom.dc.univ-lorraine.fr/scripts/collections/Events/Moodle"
            }

        elif row["eventName"] == "\mod_assign\event\\assessable_submitted":  # Dépôt d'un devoir
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_students[row["userId"]],
                            "type": "Person"
                        },
                        "action": "Submitted",
                        "object": {
                            "id": row["objectId"],
                            "type": "AssignableDigitalResource",
                            "name": get_assignment_name(row["objectId"]),
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://atom.dc.univ-lorraine.fr/scripts/collections/Events/Moodle"
            }

        elif row["component"] == "mod_quiz" and row["action"] == "submitted":  # Soumission d'un test (quiz)
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_students[row["userId"]],
                            "type": "Person"
                        },
                        "action": "Submitted",
                        "object": {
                            "id": row["objectId"],
                            "type": "Assessment",
                            "name": get_quiz_name(row["objectId"]),
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://atom.dc.univ-lorraine.fr/scripts/collections/Events/Moodle"
            }
        else:
            continue

        COUNTER_JSON_SENT += 1
        prevent_caliper_error(json, str(row["id"]), str(row["timeCreated"]))

db.close()
db_log.close()
pretty_message("Script finished",
               "Total number of events : " + str(TOTAL_EVENT) + " - Caliper Events sent: " + str(COUNTER_JSON_SENT))

MAIL = smtplib.SMTP('localhost')

MAIL.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'], "Subject: Moodle Events script finished \n\n "
              "import_events.py finished its execution \n\n -------------- \n SUMMARY \n -------------- \n" +
              "Total number of events : " + str(TOTAL_EVENT) + "\nCaliper Events sent: " + str(COUNTER_JSON_SENT))
