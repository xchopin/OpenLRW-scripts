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
import json
import re
import time

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/import_results.log', level=logging.INFO)

parser = OpenLRW.parser
parser.add_argument('-f', '--from', action='store', help='"From" timestamp for querying Moodle`s database')
parser.add_argument('-t', '--to', action='store', help='"To" timestamp for querying Moodle`s database (must be used with --from flag)')
parser.add_argument('-u', '--update', action='store_true', help='Import newer results than the last one stored in mongo')
args = vars(OpenLRW.enable_argparse())



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


def insert_grades(query, sql_where):
    query.execute(
        "SELECT users.username, grades.timemodified, grades.id, grades.finalgrade, grades.itemid,items.itemname, items.grademax, items.grademin, items.courseid, items.itemmodule "
        " FROM mdl_grade_grades as grades, mdl_user as users, mdl_grade_items as items"
        " WHERE users.id = grades.userid " + sql_where +
        " AND items.id = grades.itemid"
        " AND finalgrade IS NOT NULL"
        " AND itemname IS NOT NULL;")

    results = query.fetchall()
    JWT = OpenLrw.generate_jwt()
    line_items = json.loads(OpenLrw.get_lineitems(JWT))

    for result in results:
        student_id, date, result_id, score, lineitem_id, item_name, max_value, min_value, class_id, item_module = result

        if date > 0:
            date = str(datetime.datetime.utcfromtimestamp(date).isoformat()) + '.755Z'
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
                'type': item_module,
                'resultValueMin': str(min_value),
                'resultValueMax': str(max_value)
            }
        }

        try:
            OpenLrw.post_result_for_a_class(class_id, res_object, JWT, False)
        except ExpiredTokenException:
            JWT = OpenLrw.generate_jwt()
            OpenLrw.post_result_for_a_class(class_id, res_object, JWT, False)
        except BadRequestException as e:
            exit_log(result_id, str(e.message.content))
        except InternalServerErrorException as e:
            exit_log(result_id, str(e.message.content))
        except requests.exceptions.ConnectionError as e:
            exit_log(result_id, e)

        # Creation of Line Items

        res = False  # First we check if the lineItem already exists in the database
        item_id = 'moodle_' + str(lineitem_id)
        for i in range(0, len(line_items)):
            try:
                if line_items[i]['lineItem']['sourcedId'] == item_id:
                    res = True
                    break
            except Exception as e:
                if line_items[i]['sourcedId'] == item_id:
                    res = True
                    break

        if not res:
            item = {
                "sourcedId": item_id,
                "title": item_name,
                "description": "",
                "assignDate": "",
                "dueDate": "",
                "resultValueMax": str(max_value),
                "class": {
                    "sourcedId": class_id
                }
            }

            try:
                OpenLrw.post_lineitem(item, JWT, False)
            except ExpiredTokenException:
                JWT = OpenLrw.generate_jwt()
                OpenLrw.post_lineitem(item, JWT, False)
            except InternalServerErrorException as e:
                exit_log('Unable to create the LineItem ' + item_id, e.message.content)
            except requests.exceptions.ConnectionError as e:
                exit_log('Unable to create the LineItem ' + item_id, e)

            # Add new line item to the dynamic array
            line_items.append(item)

    return len(results)


# -------------- MAIN --------------
sql_where = ""

if (args['from'] is None) and (args['update'] is False):
    OpenLRW.pretty_error("Wrong usage", ["This script requires an argument, please run --help to get more details"])
    exit()


if args['from'] is not None and args['to'] is None:  # only from
    if re.match(TIMESTAMP_REGEX, args['from']):
        sql_where = "AND grades.timemodified >= " + args['from']
    else:
        OpenLRW.pretty_error("Wrong usage", ["Arguments must be a timestamp (FROM)"])
elif args['from'] is not None and args['to'] is not None:  # from and to
    if re.match(TIMESTAMP_REGEX, args['from']) and re.match(TIMESTAMP_REGEX, args['to']):
        sql_where = "AND grades.timemodified >= " + args['from'] + " AND grades.timemodified <= " + args['to']
    else:
        OpenLRW.pretty_error("Wrong usage", ["Arguments must be a timestamp (FROM and TO)"])
elif args['update'] is True:
    jwt = OpenLrw.generate_jwt()
    last_result = OpenLrw.http_auth_get('/api/results?page=0&limit=1', jwt)
    if last_result is None:
        OpenLrw.pretty_error("Error", "There is no result")
        OpenLrw.mail_server("Subject: Error", "Either OpenLRW is turned off either, there is no result")
        exit()
    last_result = json.loads(last_result)[0]
    date = datetime.datetime.strptime(last_result['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
    query_timestamp = (date - datetime.datetime(1970, 1, 1)).total_seconds()
    sql_where = "AND grades.timemodified > " + str(query_timestamp)


db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
query = db.cursor()


COUNTER = insert_grades(query, sql_where)

db.close()

OpenLrw.pretty_message("Script finished", "Total number of results sent : " + str(COUNTER))

message = sys.argv[0] + " executed in " + measure_time() + "seconds \n\n -------------- \n SUMMARY \n -------------- \n Total number of results sent : " + str(COUNTER)

OpenLrw.mail_server(sys.argv[0] + " executed", message)
logging.info(message)