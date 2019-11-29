#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.4"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb
import datetime
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os
import requests
import re
import json
import argparse

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *
from time import gmtime, strftime


"""
Script to send Moodle Events to OpenLRW (Caliper Events)
It queries the production database
"""

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/import_events.log', level=logging.INFO)


parser = OpenLRW.parser
parser.add_argument('-t', '--timestamps',  nargs='*', action='store', help='Two timestamps(from & to) for querying Moodle`s database')
parser.add_argument('-u', '--update', action='store_true', help='Import newer events than the last one stored in Mongo.')
args = vars(OpenLRW.enable_argparse())


def get_module_name(module_type, module_id):
    """
    Get a module name (file, url, etc...) for a type and id given
    :param module_type:  module type
    :param module_id:  module id
    :return: module name
    """
    name = "Deleted module"  # Default name if not found

    query.execute("SELECT name FROM mdl_" + module_type + " WHERE id = '" + str(module_id) + "';")
    res = query.fetchone()

    if res is not None:
        name = res[0]

    return name


def get_assignment_name(assignment_id):
    """
    Get the name of an assignment for an id given
    :param assignment_id: assignment id
    :return: assignment name
    """
    name = "Deleted assignement"  # Default name

    query.execute("SELECT name FROM mdl_assign, mdl_assign_submission "
                  "WHERE mdl_assign_submission.assignment = mdl_assign.id "
                  "AND mdl_assign_submission.id= " + str(assignment_id) + ";")
    res = query.fetchone()

    if res is not None:
        name = res[0]

    return name


def get_quiz_name(quiz_id):
    """
    Get the name of a quiz for an id given
    :param quiz_id: quiz id
    :return: quiz name
    """
    name = "Deleted quiz"  # Default name

    query.execute("SELECT name FROM mdl_quiz,mdl_quiz_attempts "
                  "WHERE mdl_quiz.id = mdl_quiz_attempts.quiz "
                  "AND mdl_quiz_attempts.id=" + str(quiz_id) + ";")
    res = query.fetchone()

    if res is not None:
        name = res[0]

    return name


def exit_log(object_id, timestamp, reason):
    """
    Stops the script and email + logs the last event
    :param object_id:
    :param timestamp:
    :param reason
    """
    db.close()
    message = "An error occured at " + strftime("%Y-%m-%d %H:%M:%S",gmtime()) + " - Event #" + str(object_id)\
              + " created at " + str(timestamp) + "\n\n Details: \n" + str(reason)

    logging.error(message)
    OpenLrw.mail_server("Error " + str(sys.argv[0]), message)
    OpenLRW.pretty_error("Error on POST", "Cannot send statement for event #" + str(object_id) + " created at " + str(timestamp))
    sys.exit(0)


def send_caliper_event(statement, object_id, timestamp):
    """
    Sends Caliper statement with checking response, if it fails it stops the execution and log + email the event that failed
    :param statement:
    :param object_id:
    :param timestamp:
    :return:
    """
    try:
        OpenLrw.send_caliper(statement)
    except OpenLRWClientException as e:
        exit_log(object_id, timestamp, str(e.message.content))
    except requests.exceptions.ConnectionError as e:
        exit_log(object_id, timestamp, e)

    # -------------- MAIN --------------


def create_caliper_json(user_id, action, object_id, object_type, object_name, description, group_id, group_type, timestamp):
    return {
        "data": [
            {
                "@context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                "@type": "Event",
                "actor": {
                    "@id": str(user_id),
                    "@type": "Person"
                },
                "action": str(action),
                "edApp": {
                    "@id": "moodle",
                    "@type": "SoftwareApplication"
                },
                "object": {
                    "@id": str(object_id),
                    "@type": str(object_type),
                    "name": str(object_name),
                    "description": description
                },
                "group": {
                    "@id":  str(group_id),
                    "@type": str(group_type)
                },
                "eventTime": str(datetime.datetime.utcfromtimestamp(timestamp).isoformat()) + '.755Z'
            }
        ],
        "sendTime": str(datetime.datetime.now().utcfromtimestamp(timestamp).isoformat()) + '.755Z',
        "sensor": str(sys.argv[0])
    }


# -------------- GLOBAL --------------

TIMESTAMP_REGEX = r'^(\d{10})?$'

DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']

COUNTER_JSON_SENT = 0
TOTAL_EVENT = 0

try:
    if (args['timestamps'] is None) and (args['update'] is False):
        OpenLRW.pretty_error("Wrong usage", ["This script requires an argument, please run --help to get more details"])
        exit()


    if args['timestamps'] is not None:
        args = args['timestamps']
        if re.match(TIMESTAMP_REGEX, args[0]) and re.match(TIMESTAMP_REGEX, args[1]):
            sql_where = "WHERE timecreated >= " + args[0]+ " AND timecreated <= " + args[1]
        else:
            OpenLrw.pretty_error("Wrong usage", ["Arguments must be a timestamp (FROM and TO)"])
    elif args['update'] is True:
        try:
            jwt = OpenLrw.generate_jwt()
            last_event = OpenLrw.http_auth_get('/api/events/sources/moodle?page=0&limit=1', jwt)

            if last_event is None:
                OpenLrw.pretty_error("NO MOODLE EVENTS", "There is no Moodle events, please use timestamps argument instead")
                OpenLrw.mail_server("Subject: Error", "Either OpenLRW is turned off either there is no Moodle events.")
                exit()

            last_event = json.loads(last_event)[0]
            date = datetime.datetime.strptime(last_event['eventTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            timestamp = (date - datetime.datetime(1970, 1, 1)).total_seconds()
            sql_where = "WHERE timecreated > " + str(timestamp)
        except:
            OpenLrw.pretty_error("NO MOODLE EVENTS",
                                 "There is no Moodle events, please use timestamps argument instead")
            OpenLrw.mail_server("Subject: Error", "Either OpenLRW is turned off either there is no Moodle events.")
            exit()



    mysql_config = {
        'host': DB_HOST,
        'user': DB_USERNAME,
        'passwd': DB_PASSWORD,
        'db': DB_NAME,
        'charset': 'utf8mb4'
    }
    db = MySQLdb.connect(**mysql_config)
    query = db.cursor()

    # Map Moodle user id to their CAS uid
    query.execute("SELECT id, username FROM mdl_user WHERE deleted=0 AND username LIKE '%u';")
    users = query.fetchall()
    moodle_students = {}
    for user in users:
        moodle_students[user[0]] = user[1]

    #  Map Moodle course ids to their name
    query.execute("SELECT id, fullname FROM mdl_course;")
    courses = query.fetchall()
    moodle_courses = {}
    for course in courses:
        moodle_courses[course[0]] = course[1]


    query.execute(
        "SELECT userid, courseid, eventname, component, action, target, objecttable, objectid, timecreated, id "
        "FROM mdl_logstore_standard_log " + sql_where)

    rows_log = query.fetchall()

    TOTAL_EVENT = len(rows_log)

    for row_log in rows_log:
        row = None  # Clears previous buffer
        row = {"userId": row_log[0], "courseId": row_log[1], "eventName": row_log[2], "component": row_log[3],
               "action": row_log[4], "target": row_log[5], "objecttable": row_log[6], "objectId": row_log[7],
               "timeCreated": row_log[8], "id": row_log[9]}

        if row["userId"] in moodle_students:  # Checks if users isn't deleted from the db
            if row["courseId"] in moodle_courses:  # Checks if the course given exists in Moodle
                course_name = moodle_courses[row["courseId"]]
            else:
                course_name = "Deleted Course"

            if row["eventName"] == "\core\event\course_viewed":  # Course viewed
                json = create_caliper_json(moodle_students[row["userId"]], "Viewed", row["courseId"], "CourseSection",
                                           course_name, "", row["courseId"], "CourseSection", row["timeCreated"]
                )
            elif row["target"] == "course_module" and row["action"] == "viewed": # Module viewed
                json = create_caliper_json(moodle_students[row["userId"]], "Viewed", row["objectId"], "DigitalResource",
                                           get_module_name(row["objecttable"], row["objectId"]), row["component"],
                                           row["courseId"], "CourseSection", row["timeCreated"]
                )

            elif row["eventName"] == "\mod_assign\event\\assessable_submitted":  # Exam submitted
                json = create_caliper_json(moodle_students[row["userId"]], "Submitted", row["objectId"], "AssignableDigitalResource",
                                           get_assignment_name(row["objectId"]), "", row["courseId"], "CourseSection", row["timeCreated"]
                )

            elif row["component"] == "mod_quiz" and row["action"] == "submitted":  # Quiz submitted
                json = create_caliper_json(moodle_students[row["userId"]], "Submitted", row["objectId"],
                                           "Assessment", get_quiz_name(row["objectId"]), "", row["courseId"], "CourseSection",
                                           row["timeCreated"]
                )

            else:
                continue

            COUNTER_JSON_SENT += 1
            send_caliper_event(json, str(row["id"]), str(row["timeCreated"]))

    db.close()

    OpenLRW.pretty_message("Script executed", "Total number of events : " + str(TOTAL_EVENT) + " - Caliper Events sent: " + str(COUNTER_JSON_SENT))

    message = str(sys.argv[0]) + " finished its execution in " + measure_time()
    message += " seconds \n\n -------------- \n SUMMARY \n -------------- \n Total number of events : "
    message += str(TOTAL_EVENT) + "\nCaliper Events sent: " + str(COUNTER_JSON_SENT)

    # OpenLrw.mail_server(str(sys.argv[0] + " executed"), message)
    logging.info(message)
except Exception as e:
    print(repr(e))
    OpenLrw.mail_server(str(sys.argv[0]) + ' error', repr(e))
    logging.error(repr(e))
    exit()
