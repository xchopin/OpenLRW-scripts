#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.2"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"


import json
import sys, os
import csv
import requests
sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *
from datetime import datetime, timedelta
import glob
import time

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/import_civic_information.log', level=logging.INFO)
OpenLRW.enable_argparse()  # Otherwise it creates an error


def exit_log(user_id, reason):
    """
    Stops the script and emails + logs the last user
    :param user_id:
    :param reason:
    """
    subject = "Error: " + str(sys.argv[0])
    message = "An error occured on user" + str(user_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(subject, message)
    logging.error(message)
    OpenLrw.pretty_error("Error", "User " + str(user_id))
    sys.exit(0)


csv_file = open('data/Users/baccalaureat_student.csv', 'r')


URI = SETTINGS['api']['uri'] + '/api'
COUNTER = 0
MAIL = None
CIVIC_INFORMATION_DIRECTORY = SETTINGS['apogee']['civic_information_directory']


def last_files(days=1):
    """
    Retrieve the last files (format has to be like Ymd.csv eg: example_20191024_test.csv)
    :return:
    """
    yesterday = datetime.now() - timedelta(days=days)
    yesterday = yesterday.strftime('%Y%m%d')
    return glob.glob(CIVIC_INFORMATION_DIRECTORY + '*' + yesterday + '*.csv')


def treat_last_files():
    files_to_import = last_files()
    counter = 0
    for file in files_to_import:
        counter += parse_file(file)
    return counter


def parse_file(filename):
    counter = 0
    users = list(csv.reader(open(filename, 'r'), delimiter=';'))
    JWT = OpenLrw.generate_jwt()

    for user in users:
        user_id = user[0]

        information = user[1].split('-')  # create an array of the concatenated string
        birth_year = information[0]
        gender = information[1]
        children = information[2]
        handicap = information[3]
        has_scholarship = information[4] == 'O'
        has_job = information[5] == 'O'
        has_adapted_study_plan = information[6] == 'O'
        city = information[7]
        bac_year = information[8]
        bac_type = information[9]
        bac_zipcode = information[10]
        bac_honor = information[11]


        try:
            user_object = OpenLrw.get_user(user_id, JWT)
        except ExpiredTokenException:
            JWT = OpenLrw.generate_jwt()
            user_object = OpenLrw.get_user(user_id, JWT)

        if user_object:
            user = json.loads(user)
            user["metadata"]["birth_year"] = birth_year
            user["metadata"]["gender"] = gender
            user["metadata"]["children"] = children
            user["metadata"]["handicap"] = handicap
            user["metadata"]["has_scholarship"] = has_scholarship
            user["metadata"]["has_job"] = has_job
            user["metadata"]["has_adapted_study_plan"] = has_adapted_study_plan
            user["metadata"]["city"] = city
            user["metadata"]["bac_year"] = bac_year
            user["metadata"]["bac_type"] = bac_type
            user["metadata"]["bac_zipcode"] = bac_zipcode
            user["metadata"]["bac_honor"] = bac_honor

            try:
                OpenLrw.post_user(user, JWT, True)  # Replace the user with the new value
            except ExpiredTokenException:
                JWT = OpenLrw.generate_jwt()
                OpenLrw.post_user(user, JWT, True)  # Replace the user with the new value
            except InternalServerErrorException as e:
                exit_log('Unable to update the user ' + user_id, e.message.content)
            except requests.exceptions.ConnectionError as e:
                exit_log('Unable to update the user ' + user_id, e)

            counter += 1

    return counter


COUNTER = treat_last_files()

time = measure_time()

OpenLrw.mail_server(sys.argv[0] + " executed", str(COUNTER) + " users updated in " + measure_time() + " seconds")
logging.info(str(COUNTER) + " users updated in " + measure_time() + " seconds")