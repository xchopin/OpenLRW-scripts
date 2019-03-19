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

classes_with_bali = []
for klass in classes:
    try:
        if klass['klass']['metadata']["populationBali"]:
            classes_with_bali.append(klass)
    except TypeError:
        pass  # population is not defined, we don't care
lineitems_to_fix = []
for result in results:
    lineItem = {'sourcedId': result['lineitem']['sourcedId']}
    if lineItem not in lineitems_to_fix:
        lineitems_to_fix.append(lineItem)


LINEITEM_TOTAL = len(lineitems_to_fix)
# Parse the file to get the "ELP" element in the first by matching the LineItem sourcedId
f1 = open(GRADES_FILE, 'r')
with f1:
    c1 = csv.reader(f1, delimiter=";")
    for row in c1:
        dip, vet, elp, per, ses, gpe = row[0], row[1], row[2], row[3], row[4], row[5]
        for lineItem in lineitems_to_fix:
            if lineItem["sourcedId"] in elp:
                for klass in classes_with_bali:
                    bali = klass["klass"]["metadata"]["populationBali"]
                    if vet in bali or elp in bali:
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
