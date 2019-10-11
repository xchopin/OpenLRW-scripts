#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.1.3"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import hashlib
import sys
import os
import requests
import csv
import json

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *
from datetime import datetime, timedelta
import glob
import time

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                    filename=os.path.dirname(__file__) + '/import_results.log', level=logging.INFO)

parser = OpenLRW.parser
parser.add_argument('-l', '--last',  action='store_true', help='Parse the files from yesterday')
parser.add_argument('-u', '--update', action='store_true', help='Make a diff between the files from yesterday and two days ago')

args = vars(OpenLRW.enable_argparse())

OpenLRW.enable_argparse()  # Otherwise it creates an error

# -------------- GLOBAL --------------
URI = SETTINGS['api']['uri'] + '/api'
RESULT_COUNTER = 0
LINEITEM_COUNTER = 0
MAIL = None
LINEITEMS_FILE = SETTINGS['apogee']['lineitems_name_filepath']
RESULTS_DIRECTORY = SETTINGS['apogee']['results_directory']

if LINEITEMS_FILE is None or LINEITEMS_FILE == "":
    OpenLrw.pretty_error("Settings parameter not filled",
                         "'lineitems_name_filepath' parameter from settings.yml is empty")


def exit_log(result_id, reason):
    """
    Stops the script and email + logs the last event
    :param result_id:
    :param reason:
    """
    subject = "Error Apogée Results"
    message = "An error occured when sending the result " + str(result_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(subject, message)
    logging.error(message)
    OpenLrw.pretty_error("Error on POST", "Cannot send the result object " + str(result_id))
    sys.exit(0)



def get_mongo_lineitems():
    JWT = OpenLrw.generate_jwt()
    mongo_lineitems = OpenLrw.get_lineitems(JWT)

    if mongo_lineitems is None:
        return {}
    else:
        mongo_lineitems = json.loads(mongo_lineitems)
        res = {}
        for item in mongo_lineitems:
            res[item['lineItem']['sourcedId']] = True
        return res


def create_lineitem(grade, lineitem_mapping, JWT, mongo_lineitems):
    title = "null"
    for line in lineitem_mapping:
        code_elp, name, etp = line
        if code_elp == grade['exam_id']:
            title = name

    item = {
        "sourcedId": grade['exam_id'],
        "lineItem": {
            "sourcedId": grade['exam_id']
        },
        "title": title,
        "description": "null",
        "assignDate": "",
        "dueDate": "",
        "class": {
            "sourcedId": "unknown_apogee"
        }
    }

    # Add new lineItem to the dynamic array
    mongo_lineitems[item['lineItem']['sourcedId']] = True

    try:
        OpenLrw.post_lineitem(item, JWT, False)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_lineitem(item, JWT, False)
    except InternalServerErrorException as e:
        exit_log(grade['exam_id'], e.message.content)
    except requests.exceptions.ConnectionError as e:
        exit_log('Unable to create the LineItem ' + grade['exam_id'], e)

    return mongo_lineitems


def last_files(days=1):
    """
    Return the latest results files
    """
    yesterday = datetime.now() - timedelta(days=days)
    yesterday = yesterday.strftime('%Y%m%d')
    return glob.glob(RESULTS_DIRECTORY + '*' + yesterday + '*.csv')


def difference(old_file, new_file):
    """
    Make a difference between an old csv file and a new one; get the full row if it's different
    :return:
    """

    old_results = list(csv.reader(open(old_file, 'r'), delimiter=';'))
    new_results = list(csv.reader(open(new_file, 'r'), delimiter=';'))
    diff_result = list()
    for x in range(len(new_results)):
        try:
            if new_results[x] != old_results[x]:
                diff_result.append(new_results[x])
        except IndexError:  # it means it's a new line that old_results don't have (so it's new!)
            diff_result.append(new_results[x])

    counter = parse_results(new_file, diff_result)

    return counter


def update():
    yesterday_files = last_files()  # most recents
    two_days_ago_files = last_files(2)  # previous files

    if len(yesterday_files) is not len(two_days_ago_files):
        message = "Not enough file to make a difference : Yesterday has " + str(len(yesterday_files)) +\
                  " files but 2 days ago has " + str(len(two_days_ago_files)) + " files."
        logging.error(message)
        OpenLrw.mail_server("Error Apogee results (Missing file)", message)
        OpenLrw.pretty_error("Missing file", "Impossible to make a difference, please check the log file.")
        sys.exit(0)

    counter = 0

    for x in range(len(yesterday_files)):
        print(yesterday_files[x])
        counter += difference(two_days_ago_files[x], yesterday_files[x])

    return counter





def parse_results(filename, results):
    counter = 0
    lineitem_mapping = list(csv.reader(open(LINEITEMS_FILE, "rb"), delimiter=';'))
    mongo_lineitems = get_mongo_lineitems()
    is_file_corrupted = False
    for user_result in results:
        username = user_result[0]
        year = user_result[1]
        degree_id = user_result[2]
        degree_version = user_result[3]
        inscription = user_result[4]
        term_id = user_result[5]
        term_version = user_result[6]

        for x in range(7, len(user_result)):  # many grades on this column
            data = user_result[x].split('-')
            try:
                grade = {'type': data[0], 'exam_id': data[1], 'score': data[2], 'status': None}
            except IndexError as e:
                message = str(e) + ' for ' + str(data) + ' - should have 3 values (type, exam_id and score)'
                logging.error(message)
                is_file_corrupted = True
                pass

            if len(data) > 3:
                grade['status'] = data[3]

            string = str(username) + str(grade['exam_id']) + str(year) + str(grade['type'])
            sourcedId = hashlib.sha1(string)

            data = {
                'sourcedId': str(sourcedId.hexdigest()),
                'score': str(grade['score']),
                'resultStatus': grade['status'],
                'student': {
                    'sourcedId': username
                },
                'lineitem': {
                    'sourcedId': grade['exam_id']
                },
                'metadata': {
                    'type': grade['type'],
                    'year': year,
                    'category': 'Apogée'
                }
            }

            # Check if LineItem already exists
            exist = False
            try:
                if mongo_lineitems[grade['exam_id']]:
                    exist = True
                    pass
            except KeyError:
                exist = False

            # If the LineItem does not exist we have to create it
            if exist is False:
                mongo_lineitems = create_lineitem(grade, lineitem_mapping, JWT, mongo_lineitems)

            post_result(data, 'unknown_apogee', JWT)  # in any cases we have to send the result
            counter += 1

    if is_file_corrupted is True:
        message = str(filename) + ' is corrupted, check the log file for more details'
        OpenLrw.mail_server("Apogée Result - CSV File corrupted", message)

    return counter



def parse_results_file(file):
    users_results = list(csv.reader(open(file, 'r'), delimiter=';'))
    counter = parse_results(file, users_results)

    return counter


def post_result(data, class_id, JWT):
    try:
        OpenLrw.post_result_for_a_class(class_id, data, JWT, True)
    except ExpiredTokenException:
        JWT = OpenLrw.generate_jwt()
        OpenLrw.post_result_for_a_class(class_id, data, JWT, True)
    except BadRequestException as e:
        exit_log(data['lineitem']['sourcedId'], e.message.content)
    except InternalServerErrorException as e:
        exit_log(data['lineitem']['sourcedId'], e.message.content)
    except requests.exceptions.ConnectionError as e:
        exit_log('Unable to post the result for the class unknown_apogee', e)


def import_last_results():
    files_to_import = last_files()
    counter = 0
    for file in files_to_import:
        counter += parse_results_file(file)
    return counter


# -------------- MAIN --------------

if (args['last'] is False) and (args['update'] is False):
    OpenLRW.pretty_error("Wrong usage", ["This script requires an argument, please run --help to get more details"])
    exit()

JWT = OpenLrw.generate_jwt()

# Create a temporary class
try:
    response = requests.post(URI, headers={'Authorization': 'Bearer ' + JWT}, json={'sourcedId': 'unknown_apogee', 'title': 'Temporary Apogee class'})
    if response == 500:
        exit_log('Unable to create the Class "Apogée"', response)
except requests.exceptions.ConnectionError as e:
    exit_log('Unable to create the Class "Apogée"', e)


if args['last'] is True:
    RESULT_COUNTER = import_last_results()
elif args['update'] is True:
    RESULT_COUNTER = update()


LINEITEM_COUNTER = 0

OpenLrw.pretty_message("Script finished", "Results sent: " + str(RESULT_COUNTER))
message = "Script executed in " + measure_time() + " seconds \n\n -------------- \n SUMMARY \n -------------- \n" \
          + str(RESULT_COUNTER) + " results sent \n "
OpenLrw.mail_server(sys.argv[0] + " executed", message)
logging.info(message)

