#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.2"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import datetime
import sys
import os
import requests
import datetime
import csv
import uuid
import json
sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/map_classes.log', level=logging.INFO)

COUNTER = 0
GRADES_FILE = 'data/LineItems/mapping.csv'


def exit_log(reason):
    """
    Stops the script and email + logs the last event
    :param result_id:
    :param reason:
    """
    message = "An error occured: " + str(reason)
    OpenLrw.mail_server("Error " + sys.argv[0], message)
    logging.error(message)
    OpenLrw.pretty_error("Error on POST", "Check the email content or the log file")
    sys.exit(0)


# -------------- MAIN --------------


OpenLRW.pretty_message("CSV File used for the import", GRADES_FILE)

JWT = OpenLrw.generate_jwt()

lineitems = OpenLrw.http_auth_get('/api/classes/unknown_apogee/lineitems', JWT)
classes = OpenLrw.http_auth_get('/api/classes', JWT)

if lineitems is None:
    OpenLrw.pretty_error('Empty Collection', 'You have to populate the LineItem collection before using this script')

if classes is None:
    OpenLrw.pretty_error('Empty Collection', 'You have to populate the Class collection before using this script')


lineitems_to_fix = json.loads(lineitems)

classes = json.loads(classes)

classes_with_classcode = []
for klass in classes:
    try:
        if klass['klass']['metadata']["classCode"]:
            classes_with_classcode.append(klass)
    except TypeError:
        pass  # classCode is not defined, let skip

LINEITEM_TOTAL = len(lineitems_to_fix)

# Parse the file to get the "ELP" element in the first by matching the LineItem sourcedId
for lineItem in lineitems_to_fix:
    for klass in classes_with_classcode:
        classcodes = klass["klass"]["metadata"]["classCode"]

        array_of_classcodes = classcodes.split(',')

        for classcode in array_of_classcodes:
            if classcode == lineItem['sourcedId']:
                data = {
                    "sourcedId": lineItem["sourcedId"],
                    "class": {
                        "sourcedId": klass["classSourcedId"],
                        "title": lineItem["title"]
                    }
                }
                COUNTER = COUNTER + 1
                try:
                    OpenLrw.post_lineitem(data, JWT, True)
                except ExpiredTokenException:
                    JWT = OpenLrw.generate_jwt()
                    OpenLrw.post_lineitem(data, JWT, True)
                except InternalServerErrorException as e:
                    exit_log('Unable to create the LineItem ' + lineItem["sourcedId"], e.message.content)
                except requests.exceptions.ConnectionError as e:
                    exit_log('Unable to create the LineItem ' + lineItem["sourcedId"], e)







OpenLrw.pretty_message("Script finished", "Total number of line items edited : " + str(COUNTER))

message = sys.argv[0] + "(Mapping Apogée CSV and Results) executed in " + measure_time() + " seconds \n\n -------------- \n SUMMARY \n -------------- \n" + "LineItems edited : " + str(COUNTER) + " on " + str(LINEITEM_TOTAL)

OpenLrw.mail_server(sys.argv[0] + " executed", message)
logging.info(message)