#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.6"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb
import sys
import os
import requests
import datetime
import json

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.dirname(__file__) + '/import_lineitems.log', level=logging.INFO)
OpenLRW.enable_argparse()  # Otherwise it creates an error

# -------------- GLOBAL --------------
DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']
COUNTER = 0


def exit_log(lineitem_id, reason):
    """
    Stops the script and email + logs the last event
    :param lineitem_id:
    :param reason:
    """
    message = "Error Moodle line item \n\n An error occured when sending the line item " + str(
        lineitem_id) + "\n\n Details: \n" + str(reason)
    OpenLrw.mail_server(" Error Moodle line item", message)
    logging.error(message)
    OpenLrw.pretty_error("Error on POST", "Cannot send the line item object " + str(lineitem_id))
    sys.exit(0)


def generate_json(sourced_id, title, description, assign_date, due_date, class_sourced_id, category, result_value_max,result_value_min):
    """
    Generate a JSON formatted value ready to be sent to OpenLRW
    :param sourced_id:
    :param title:
    :param description:
    :param assign_date:
    :param due_date:
    :param class_sourced_id:
    :param category:
    :param result_value_max:
    :param result_value_min
    :return:
    """
    if result_value_max is None:
        result_value_max = 0.0

    if result_value_min is None:
        result_value_min = 0.0

    return {
        "sourcedId": sourced_id,
        "title": title,
        "description": description,
        "assignDate": assign_date,
        "dueDate": due_date,
        "resultValueMax": result_value_max,
        "resultValueMin": result_value_min,
        "class": {
            "sourcedId": class_sourced_id
        },
        "metadata": {
            "type": category
        }
    }


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


def import_module(module, cursor, mongo_lineitems):
    counter = 0
    cursor.execute("SELECT id, course, name, intro, timemodified FROM mdl_" + module + ";")
    line_items = cursor.fetchall()
    JWT = OpenLrw.generate_jwt()

    for line_item in line_items:
        exist = False
        id, class_id, name, description, date_open = line_item
        item_id = module + '_' + str(id)

        # Check if LineItem already exists
        try:
            if mongo_lineitems[item_id]:
                break
        except KeyError:
            exist = False

        date_open = str(datetime.datetime.now().utcfromtimestamp(date_open).isoformat()) + '.755Z' if date_open > 0 else None

        if exist is False:
            data = generate_json(item_id, name, description, date_open, None, class_id, module, None, None)
            try:
                OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, False)
                counter += 1
            except ExpiredTokenException:
                JWT = OpenLrw.generate_jwt()
                OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, False)
                counter += 1
            except BadRequestException as e:
                exit_log(item_id, e.message.content)
            except InternalServerErrorException:
                exit_log(item_id, "Internal Server Error 500")
            except requests.exceptions.ConnectionError as e:
                exit_log(item_id, e)

    return counter


def import_other_module(cursor, mongolineitems):
    counter = 0
    cursor.execute("SELECT grades.itemid, items.courseid, items.itemname, items.timemodified "
                   "FROM mdl_grade_grades as grades, mdl_user as users, mdl_grade_items as items "
                   "WHERE users.id = grades.userid "
                   "AND items.id = grades.itemid "
                   "AND finalgrade IS NOT NULL "
                   "AND itemname IS NOT NULL "
                   "AND itemmodule IS NULL "
                   "GROUP BY itemid")
    line_items = cursor.fetchall()
    JWT = OpenLrw.generate_jwt()

    for line_item in line_items:
        exist = False
        id, class_id, name, date_open = line_item
        item_id = 'other_' + str(id)

        # Check if LineItem already exists
        try:
            if mongo_lineitems[item_id]:
                break
        except KeyError:
            exist = False

        date_open = str(datetime.datetime.now().utcfromtimestamp(date_open).isoformat()) + '.755Z' if date_open > 0 else None

        if exist is False:
            data = generate_json(item_id, name, "", date_open, None, class_id, "other", None, None)
            try:
                OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, False)
                counter += 1
            except ExpiredTokenException:
                JWT = OpenLrw.generate_jwt()
                OpenLrw.post_lineitem_for_a_class(class_id, data, JWT, False)
                counter += 1
            except BadRequestException as e:
                exit_log(item_id, e.message.content)
            except InternalServerErrorException:
                exit_log(item_id, "Internal Server Error 500")
            except requests.exceptions.ConnectionError as e:
                exit_log(item_id, e)

    return counter


# -------------- MAIN --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
cursor = db.cursor()
cursor.execute("SELECT itemmodule FROM mdl_grade_items WHERE itemmodule IS NOT NULL GROUP BY itemmodule;")
modules = cursor.fetchall()

mongo_lineitems = get_mongo_lineitems()

for module in modules:
    module_name = module[0]
    COUNTER += import_module(str(module_name), cursor, mongo_lineitems)

COUNTER += import_other_module(cursor, mongo_lineitems)

db.close()

OpenLRW.pretty_message("Script finished", "Total number of line items sent : " + str(COUNTER))

message = str(sys.argv[0]) + " finished its execution in " + measure_time() + " seconds\n\n -------------- \n SUMMARY \n -------------- \n" + "Total number of line items sent : " + str(COUNTER)

OpenLrw.mail_server(str(sys.argv[0] + " executed"), message)
logging.info(message)
