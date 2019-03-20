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


# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()

# Query to get quizzes
query.execute("SELECT username, grades.id, grades.quiz, grades.grade, grades.timemodified, quiz.course"
              " FROM mdl_user as users, mdl_quiz_grades as grades, mdl_quiz as quiz"
              " WHERE grades.quiz = quiz.id AND users.id = grades.userid")

results = query.fetchall()

JWT = OpenLrw.generate_jwt()

for result in results:
    student_id, result_id, lineitem_id, score, date, class_id = result

    if date > 0:
        date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%dT%H:%M:%S.755Z')
    else:
        date = ""

    json = {
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
        OpenLrw.post_result_for_a_class(class_id, json, JWT, False)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_result_for_a_class(class_id, json, JWT, False)
    except BadRequestException as e:
        print("Error " + str(e.message.content))
        OpenLrw.mail_server("Error import_results.py", str(e.message.content))
    except InternalServerErrorException as e:
        exit_log(result_id, str(e.message.content))
    except requests.exceptions.ConnectionError as e:
        exit_log(result_id, e)

COUNTER = len(results)

# Query to get active quizzes
query.execute(
    "SELECT username, grades.id, activequiz.id, grades.finalgrade, grades.feedback, grades.timemodified, activequiz.course"
    " FROM mdl_user as users, mdl_activequiz as activequiz, mdl_grade_grades as grades, mdl_grade_items as items"
    " WHERE grades.itemid = items.id AND items.courseid = activequiz.course"
    " AND users.id = grades.userid AND grades.finalgrade is NOT NULL")

results = query.fetchall()

for result in results:
    student_id, result_id, lineitem_id, score, feedback, date, class_id = result

    if date > 0:
        date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%dT%H:%M:%S')
    else:
        date = ""

    if feedback is None:
        json = {
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
        json = {
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
        OpenLrw.post_result_for_a_class(class_id, json, JWT, False)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_result_for_a_class(class_id, json, JWT, False)
    except BadRequestException as e:
        print("Error " + str(e.message.content))
        OpenLrw.mail_server("Error import_results.py", str(e.message.content))
    except InternalServerErrorException as e:
        exit_log(result_id, str(e.message.content))
    except requests.exceptions.ConnectionError as e:
        exit_log(result_id, e)

COUNTER = COUNTER + len(results)
db.close()

OpenLrw.pretty_message("Script finished", "Total number of results sent : " + str(COUNTER))

message = sys.argv[0] + " executed in " + measure_time() + "seconds " \
           "\n\n -------------- \n SUMMARY \n -------------- \n Total number of results sent : " + str(COUNTER)

OpenLrw.mail_server(sys.argv[0] + " executed", message)