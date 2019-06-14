#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.2"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb
import sys
import os
import requests
import datetime
import json
import re
import time

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/import_results.log', level=logging.ERROR)

# -------------- GLOBAL --------------
DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']

URI = SETTINGS['api']['uri'] + '/api/classes/'
MAIL = None
COUNTER = 0


def exit_log(result_id, reason):
    """
    Stops the script and email + logs the last event
    :param result_id:
    :param reason:
    """
    db.close()
    message = "An error occured when sending the result " + str(result_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server("Error Moodle Results", message)
    logging.error(message)
    OpenLRW.pretty_error("Error on POST", "Cannot send the result object " + str(result_id))
    sys.exit(0)


def insert_quizzes(query, sql_where):
    # Query to get quizzes
    query.execute("SELECT username, grades.id, grades.quiz, grades.grade, grades.timemodified, quiz.course"
                  " FROM mdl_user as users, mdl_quiz_grades as grades, mdl_quiz as quiz"
                  " WHERE grades.quiz = quiz.id AND users.id = grades.userid " + sql_where)

    results = query.fetchall()

    JWT = OpenLrw.generate_jwt()

    for result in results:
        student_id, result_id, lineitem_id, score, date, class_id = result

        if date > 0:
            date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%dT%H:%M:%S.755Z')
        else:
            date = ""

        result = {
            'sourcedId': result_id,
            'score': str(score),
            'date': date,
            'student': {
                'sourcedId': student_id
            },
            'lineitem': {
                'sourcedId': 'quiz_' + str(lineitem_id)
            },
            'metadata': {
                'category': 'Moodle',
                'type': 'quiz'
            }
        }

        try:
            OpenLrw.post_result_for_a_class(class_id, result, JWT, True)
        except ExpiredTokenException:
            JWT = OpenLrw.generate_jwt()
            OpenLrw.post_result_for_a_class(class_id, result, JWT, True)
        except BadRequestException as e:
            print("Error " + str(e.message.content))
            OpenLrw.mail_server("Error import_results.py", str(e.message.content))
        except InternalServerErrorException as e:
            exit_log(result_id, str(e.message.content))
        except requests.exceptions.ConnectionError as e:
            exit_log(result_id, e)

    return len(results)


def insert_active_quizzes(query, sql_where):
    # Query to get active quizzes
    query.execute(
        "SELECT username, grades.id, activequiz.id, grades.finalgrade, grades.feedback, grades.timemodified, activequiz.course"
        " FROM mdl_user as users, mdl_activequiz as activequiz, mdl_grade_grades as grades, mdl_grade_items as items"
        " WHERE grades.itemid = items.id AND items.courseid = activequiz.course " + sql_where +
        " AND users.id = grades.userid AND grades.finalgrade is NOT NULL")

    results = query.fetchall()

    JWT = OpenLrw.generate_jwt()

    for result in results:
        student_id, result_id, lineitem_id, score, feedback, date, class_id = result

        if date > 0:
            date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%dT%H:%M:%S.755Z')
        else:
            date = ""

        if feedback is None:
            result = {
                'sourcedId': result_id,
                'score': str(score),
                'date': date,
                'student': {
                    'sourcedId': student_id
                },
                'lineitem': {
                    'sourcedId': 'active_quiz_' + str(lineitem_id)
                },
                'metadata': {
                    'category': 'Moodle',
                    'type': 'active_quiz'
                }
            }
        else:
            result = {
                'sourcedId': result_id,
                'score': str(score),
                'date': date,
                'student': {
                    'sourcedId': student_id
                },
                'lineitem': {
                    'sourcedId': 'active_quiz_' + str(lineitem_id)
                },
                'metadata': {
                    'category': 'Moodle',
                    'type': 'active_quiz',
                    'feedback': feedback
                }
            }

        try:
            OpenLrw.post_result_for_a_class(class_id, result, JWT, True)
        except ExpiredTokenException:
            JWT = OpenLrw.generate_jwt()
            OpenLrw.post_result_for_a_class(class_id, result, JWT, True)
        except BadRequestException as e:
            print("Error " + str(e.message.content))
            OpenLrw.mail_server("Error import_results.py", str(e.message.content))
        except InternalServerErrorException as e:
            exit_log(result_id, str(e.message.content))
        except requests.exceptions.ConnectionError as e:
            exit_log(result_id, e)

    return len(results)


def insert_grades(query, sql_where):
    query.execute(
        "SELECT users.username, grades.timemodified, grades.id, grades.finalgrade, grades.itemid,items.itemname, items.grademax, items.grademin, items.courseid"
        " FROM mdl_grade_grades as grades, mdl_user as users, mdl_grade_items as items"
        " WHERE users.id = grades.userid " + sql_where +
        " AND items.id = grades.itemid"
        " AND finalgrade IS NOT NULL"
        " AND itemname IS NOT NULL;")

    results = query.fetchall()
    JWT = OpenLrw.generate_jwt()
    line_items = json.loads(OpenLrw.get_lineitems(JWT))

    for result in results:
        student_id, date, result_id, score, lineitem_id, item_name, max_value, min_value, class_id = result

        if date > 0:
            date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%dT%H:%M:%S.755Z')
        else:
            date = ""

        # Creation of the Result object
        res_object = {
            'sourcedId': result_id,
            'score': str(score),
            'date': date,
            'student': {
                'sourcedId': student_id
            },
            'lineitem': {
                'sourcedId': 'grade_item_' + str(lineitem_id)
            },
            'metadata': {
                'category': 'Moodle',
                'type': 'grade_result',
                'resultValueMin': str(min_value),
                'resultValueMax': str(max_value)
            }
        }

        try:
            OpenLrw.post_result_for_a_class(class_id, res_object, JWT, True)
        except ExpiredTokenException:
            JWT = OpenLrw.generate_jwt()
            OpenLrw.post_result_for_a_class(class_id, res_object, JWT, True)
        except BadRequestException as e:
            print("Error " + str(e.message.content))
            OpenLrw.mail_server("Error import_results.py", str(e.message.content))
        except InternalServerErrorException as e:
            exit_log(result_id, str(e.message.content))
        except requests.exceptions.ConnectionError as e:
            exit_log(result_id, e)

        # Creation of Line Items

        res = False  # First we check if the lineItem already exists in the database
        item_id = 'grade_item_' + str(lineitem_id)
        for i in range(0, len(line_items)):
            if line_items[i]['lineItem']['sourcedId'] == item_id:
                res = True
                break

        if not res:
            item = {
                "sourcedId": item_id,
                "title": item_name,
                "assignDate": "",
                "dueDate": "",
                "class": {
                    "sourcedId": class_id
                },
                "lineItem": {
                    "sourcedId": item_id
                }
            }

            try:
                OpenLrw.post_lineitem(item, JWT, True)
            except ExpiredTokenException:
                JWT = OpenLrw.generate_jwt()
                OpenLrw.post_lineitem(item, JWT, True)
            except InternalServerErrorException as e:
                exit_log('Unable to create the LineItem ' + item_id, e.message.content)
            except requests.exceptions.ConnectionError as e:
                exit_log('Unable to create the LineItem ' + item_id, e)

            # Add new line item to the dynamic array
            line_items.append(item)

    return len(results)


# -------------- MAIN --------------
OpenLrw.pretty_message("Caution", "For a better performance, make sure MongoDB indices are created.")
time.sleep(0.7)
sql_where = ""

# If the script runs with arguments we use them
if len(sys.argv) == 2:
    if re.match(TIMESTAMP_REGEX, sys.argv[1]):
        sql_where = "AND grades.timemodified >= " + sys.argv[1]
    else:
        OpenLRW.pretty_error("Wrong usage", ["Arguments must be a timestamp (FROM)"])
elif len(sys.argv) == 3:
    if re.match(TIMESTAMP_REGEX, sys.argv[1]) and re.match(TIMESTAMP_REGEX, sys.argv[2]):
        sql_where = "AND grades.timemodified >= " + sys.argv[1] + " AND grades.timemodified <= " + sys.argv[2]
    else:
        OpenLRW.pretty_error("Wrong usage", ["Arguments must be a timestamp (FROM and TO)"])

db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

quiz = insert_quizzes(query, sql_where)
active_quiz = insert_active_quizzes(query, sql_where)
items = insert_grades(query, sql_where)

COUNTER = quiz + active_quiz + items

db.close()

OpenLrw.pretty_message("Script finished", "Total number of results sent : " + str(COUNTER))

message = sys.argv[0] + " executed in " + measure_time() + "seconds \n\n -------------- \n SUMMARY \n -------------- \n Total number of results sent : " + str(COUNTER)

OpenLrw.mail_server(sys.argv[0] + " executed", message)
logging.info(message)