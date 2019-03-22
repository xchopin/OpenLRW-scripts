#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
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

logging.basicConfig(filename=os.path.dirname(__file__) + '/map_classes.log', level=logging.ERROR)

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


results = OpenLrw.oneroster_get('/api/classes/unknown_apogee/results', JWT)
classes = OpenLrw.oneroster_get('/api/classes', JWT)

results = json.loads(results)
classes = json.loads(classes)

classes_with_classcode = []
for klass in classes:
    try:
        if klass['klass']['metadata']["classCode"]:
            classes_with_classcode.append(klass)
    except TypeError:
        pass  # classCode is not defined, let skip

lineitems_to_fix = []
for result in results:
    lineItem = {'sourcedId': result['lineitem']['sourcedId']}
    if lineItem not in lineitems_to_fix:
        lineitems_to_fix.append(lineItem)

LINEITEM_TOTAL = len(lineitems_to_fix)
# Parse the file to get the "ELP" element in the first by matching the LineItem sourcedId

for lineItem in lineitems_to_fix:
        for klass in classes_with_classcode:
            classcode = klass["klass"]["metadata"]["classCode"]
            if classcode == lineItem['sourcedId']:
                response = OpenLrw.get_lineitem(lineItem['sourcedId'], JWT)
                item = json.loads(response)
                lineItem['title'] = item['lineItem']['title']
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
                break
        lineitems_to_fix.remove(lineItem)


OpenLrw.pretty_message("Script finished", "Total number of line items edited : " + str(COUNTER))

message = sys.argv[0] + "(Mapping Apogée CSV and Results) executed in " + measure_time() + " seconds \n\n -------------- \n SUMMARY \n -------------- \n" + "LineItems edited : " + str(COUNTER) + " on " + str(LINEITEM_TOTAL)

OpenLrw.mail_server(sys.argv[0] + " executed", message)
