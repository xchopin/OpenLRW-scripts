#!/usr/bin/python
# coding: utf-8

__author__ = "Benjamin Seclier, Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "benjamin.seclier@univ-lorraine.fr, xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import MySQLdb, datetime, sys, os, base64, requests
sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *


# -------------- GLOBAL --------------
API_URI = SETTINGS['api']['uri'] + '/api/'
API_USERNAME = SETTINGS['api']['username']
API_PASSWORD = SETTINGS['api']['password']

DB_LOG_HOST = SETTINGS['db_moodle_log']['host']
DB_LOG_NAME = SETTINGS['db_moodle_log']['name']
DB_LOG_USERNAME = SETTINGS['db_moodle_log']['username']
DB_LOG_PASSWORD = SETTINGS['db_moodle_log']['password']

DB_HOST = SETTINGS['db_moodle']['host']
DB_NAME = SETTINGS['db_moodle']['name']
DB_USERNAME = SETTINGS['db_moodle']['username']
DB_PASSWORD = SETTINGS['db_moodle']['password']

# -------------- DATABASES --------------
db = MySQLdb.connect(DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME)
db_log = MySQLdb.connect(DB_LOG_HOST, DB_LOG_USERNAME, DB_LOG_PASSWORD, DB_LOG_NAME)

query = db.cursor()
query_log = db_log.cursor()


# -------------- FUNCTIONS --------------
def get_module_name(type, id):
    """
    Récupère le nom d'un module (fichier, test, url, etc.) pour un type et id donné
    :param type:  module type
    :param id:  module id
    :return: module name
    """
    query.execute("SELECT name FROM mdl_" + type + " WHERE id = '" + str(id) + "';")
    res = query.fetchone()
    return res[0]


def get_assignment_name(id):
    """
    Récupère le nom d'un devoir pour un id donné
    :param id: assignment id
    :return: assignment name
    """
    query.execute("SELECT name FROM arche_prod.mdl_assign,arche_prod.mdl_assign_submission WHERE arche_prod.mdl_assign_submission.assignment = arche_prod.mdl_assign.id AND arche_prod.mdl_assign_submission.id="+str(id)+";")
    res = query.fetchone()
    return res[0]


def get_quiz_name(id):
    """
    Récupère le nom du test selon l'id de la tentative
    :param id: quiz id
    :return: quiz name
    """
    query.execute("SELECT name FROM arche_prod.mdl_quiz,arche_prod.mdl_quiz_attempts WHERE arche_prod.mdl_quiz.id = arche_prod.mdl_quiz_attempts.quiz AND arche_prod.mdl_quiz_attempts.id="+str(id)+";")
    res = query.fetchone()
    return res[0]


def send_xapi_statement(statement):
    """
    Helper function to send xAPI statements
    :param statement: JSON Object following the xAPI format
    :return: HTTP Status
    """
    credentials = base64.b64encode(API_USERNAME +':'+ API_PASSWORD)
    url = API_URI + "/xAPI/statements"
    headers = {"Authorization": "Basic "+ credentials, "X-Experience-API-Version": "1.0.0"}
    r = requests.post(url, headers=headers, json=statement)
    return r.text


def send_caliper_statement(statement):
    """
    Helper function to send Caliper IMS statement
    :param statement:
    :return: HTTP Status
    """
    url = SETTINGS['api']['uri'] + "/key/caliper"
    headers = {"Authorization": API_USERNAME}
    r = requests.post(url, headers=headers, json=statement)
    return r.text


# Création d'un dictionnaire avec les id moodle et les logins UL
# {32L: 'giretti1u', 33L: 'ostiatti1u', 34L: 'pallucca1u', 35L: 'thiery27u', 24L: 'riviere8u'}
#  moodle_users[32] => giretti1u
query.execute("SELECT id, username FROM arche_prod.mdl_user WHERE deleted=0 AND username LIKE '%u';")
users = query.fetchall()
moodle_users={}
for user in users:
    moodle_users[user[0]] = user[1]

# Création d'un dictionnaire avec les id de cours moodle et leur nom
# {1L: 'ARCHE Universit\xc3\xa9 de Lorraine', 2L: 'Espace \xc3\xa9tudiants', 3L: 'Espace enseignants', 4L: 'Podcast Premier semestre'}
# moodle_courses[3] => Espace enseignants
query.execute("SELECT id,fullname FROM arche_prod.mdl_course;")
courses = query.fetchall()
moodle_courses = {}
for course in courses:
    moodle_courses[course[0]] = course[1]

# -------------- MAIN --------------

# Query for a day | Requête pour une journée
query_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log LIMIT 10;")
# cursor_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log where component='mod_quiz' and action='submitted' LIMIT 50;")
# cursor_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log where eventname like '%assessable_submitted' LIMIT 30;")
# cursor_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log where eventname like '%course_module_viewed' LIMIT 30;")
rows_log = query_log.fetchall()

for row_log in rows_log:
    row = {} # Clear previous buffer
    row["userId"] = row_log[0]
    row["courseId"] = row_log[1]
    row["eventName"] = row_log[2]
    row["component"] = row_log[3]
    row["action"] = row_log[4]
    row["target"] = row_log[5]
    row["objecttable"] = row_log[6]
    row["objectId"] = row_log[7]
    row["timeCreated"] = row_log[8]

    # On vérifie s'il s'agit d'un utilisateur remonté dans le tableau moodle_users (étudiant non deleted)
    if row["userId"] in moodle_users:
        # print(row_log)
        # (25069L, 11813L, '\\mod_resource\\event\\course_module_viewed', 'mod_resource', 'viewed', 'resource', 301058L)

        # On récupère le titre du cours concerné (s'il est présent dans la base)
        if row["courseId"] in moodle_courses:
            course_name = moodle_courses[row["courseId"]]
        else:
            course_name = "Cours supprimé de la plateforme"

        # Visualisation d'un cours
        if row["eventName"] == "\core\event\course_viewed":
            print(moodle_users[row["userId"]] + " viewed course " + str(row["courseId"]) + " (" + course_name + ") at " + str(datetime.datetime.fromtimestamp(row["timeCreated"]).strftime('%Y-%m-%d %H:%M:%S')))
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_users[row["userId"]],
                            "type": "Person"
                        },
                        "action": "Viewed",
                        "object": {
                            "id": row["courseId"],
                            "type": "CourseSection",
                            "name": course_name,
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://scripts/collections/Events/Moodle"
            }
            print(json)
            print("---------")
            print(send_caliper_statement(json))

        # Visualisation d'un module de cours
        elif row["target"] == "course_module" and row["action"] == "viewed":
            print(moodle_users[row["userId"]] + " viewed module " + row["component"] + " (" + get_module_name(row["objecttable"], row["objectId"]) + ") in course " + str(row["courseId"]) + " (" + course_name + ") at " + str(datetime.datetime.fromtimestamp(row["timeCreated"]).strftime('%Y-%m-%d %H:%M:%S')))
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_users[row["userId"]],
                            "type": "Person"
                        },
                        "action": "Viewed",
                        "object": {
                            "id": row["objectId"],
                            "type": "DigitalResource",
                            "name": get_module_name(row["objecttable"], row["objectId"]),
                            "description": row["component"],
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://localhost/scripts/collections/Events/Moodle"
            }
            print (json)
            print ("---------")
            print (send_caliper_statement(json))

        # Dépôt d'un devoir
        elif row["eventName"] == "\mod_assign\event\\assessable_submitted":
            print(moodle_users[row["userId"]] + " depot devoir (" + get_module_name(row["objectId"]) + ") in course " + str(row["courseId"]) + " (" + course_name + ") at " + str(datetime.datetime.fromtimestamp(row["timeCreated"]).strftime('%Y-%m-%d %H:%M:%S')))
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_users[row["userId"]],
                            "type": "Person"
                         },
                        "action": "Submitted",
                        "object": {
                            "id": row["objectId"],
                            "type": "AssignableDigitalResource",
                            "name": get_assignment_name(row["objectId"]),
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://localhost/scripts/collections/Events/Moodle"
            }
            print(json)
            print("---------")
            print(send_caliper_statement(json))

        # Soumission d'un test (quiz)
        elif row["component"] == "mod_quiz" and row["action"] == "submitted":
            print(moodle_users[row["userId"]] + " soumission test (" + get_quiz_name(row["objectId"]) + ") in course " + str(row["courseId"]) + " (" + course_name + ") at " + str(datetime.datetime.fromtimestamp(row["timeCreated"]).strftime('%Y-%m-%d %H:%M:%S')))
            json = {
                "data": [
                    {
                        "context": "http://purl.imsglobal.org/ctx/caliper/v1p1",
                        "type": "Event",
                        "actor": {
                            "id": moodle_users[row["userId"]],
                            "type": "Person"
                        },
                        "action": "Submitted",
                        "object": {
                            "id": row["objectId"],
                            "type": "Assessment",
                            "name": get_quiz_name(row["objectId"]),
                        },
                        "group": {
                            "id": row["courseId"],
                            "type": "CourseSection"
                        },
                        "eventTime": datetime.datetime.fromtimestamp(row["timeCreated"]).isoformat()
                    }
                ],
                "sendTime": datetime.datetime.now().isoformat(),
                "sensor": "http://localhost/scripts/collections/Events/Moodle"
            }
            print(json)
            print("---------")
            print(send_caliper_statement(json))
        else:
            print("Autre : " + moodle_users[row["userId"]] + " " + row["action"] + " " + row["target"] + " " + str(row["timeCreated"]))

db.close()
db_log.close()
