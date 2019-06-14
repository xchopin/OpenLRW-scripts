#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"


import json
import sys, os
import csv
import requests
sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

jwt = OpenLrw.generate_jwt()  # Generate a JSON Web Token for using OneRoster routes


def exit_log(user_id, reason):
    """
    Stops the script and email + logs the last event
    :param method:
    :param user_id:
    :param reason:
    """
    subject = str(sys.argv[0])
    message = "An error occured on user" + str(user_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(subject, message)
    logging.error(message)
    OpenLrw.pretty_error("Error", "User " + str(user_id))
    sys.exit(0)


csv_file = open('data/Users/baccalaureat_student.csv', 'r')

counter = 0
with csv_file:
    has_header = csv.Sniffer().has_header(csv_file.read(1024))
    csv_file.seek(0)  # Rewind
    reader = csv.reader(csv_file, delimiter=';')

    next(reader) if has_header else None
    for row in reader:
        user_id, serie_bac, year, mention = row
        if year == '' or serie_bac == '':
            continue

        try:
            user = OpenLrw.get_user(user_id, jwt)
        except ExpiredTokenException:
            JWT = OpenLrw.generate_jwt()
            user = OpenLrw.get_user(user_id, jwt)

        if user:
            user = json.loads(user)
            user["metadata"]["bac_serie"] = serie_bac
            user["metadata"]["bac_annee"] = year
            user["metadata"]["bac_mention"] = mention

            try:
                OpenLrw.post_user(user, jwt, True)  # Replace the user with the new value
            except ExpiredTokenException:
                JWT = OpenLrw.generate_jwt()
                OpenLrw.post_user(user, jwt, True)  # Replace the user with the new value
            except InternalServerErrorException as e:
                exit_log('Unable to update the user ' + user_id, e.message.content)
            except requests.exceptions.ConnectionError as e:
                exit_log('Unable to update the user ' + user_id, e)

            counter += 1

    time = measure_time()

    OpenLrw.mail_server(sys.argv[0] + " executed", str(counter) + " users updated in " + measure_time() + " seconds")
    logging.info(str(counter) + " users updated in " + measure_time() + " seconds")