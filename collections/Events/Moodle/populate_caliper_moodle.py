#!/usr/bin/python
# coding: utf-8

import MySQLdb, datetime, sys, os, base64, requests
sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

# -------- Fonctions -------- #

#Récupère le nom d'un module (fichier, test, url, etc.) selon son id
def getNomModuleFromId(type_module,id_module):
  db_lib = MySQLdb.connect(SETTINGS['db_arche_prod']['host'], SETTINGS['db_arche_prod']['user'], SETTINGS['db_arche_prod']['pass'], SETTINGS['db_arche_prod']['db'])
  cursor_lib = db_lib.cursor()
  cursor_lib.execute("SELECT name FROM mdl_"+type_module+" WHERE id = '"+str(id_module)+"';")
  res=cursor_lib.fetchone()
  return res[0]
  db_lib.close()

#Récupère le nom du devoir selon son id
def getNomDevoirFromId(id_devoir):
  db_lib = MySQLdb.connect(SETTINGS['db_arche_prod']['host'], SETTINGS['db_arche_prod']['user'], SETTINGS['db_arche_prod']['pass'], SETTINGS['db_arche_prod']['db'])
  cursor_lib = db_lib.cursor()
  cursor_lib.execute("SELECT name FROM arche_prod.mdl_assign,arche_prod.mdl_assign_submission WHERE arche_prod.mdl_assign_submission.assignment = arche_prod.mdl_assign.id AND arche_prod.mdl_assign_submission.id="+str(id_devoir)+";")
  res=cursor_lib.fetchone()
  return res[0]
  db_lib.close()

#Récupère le nom du test selon l'id de la tentative
def getNomQuizFromId(id_quiz):
  db_lib = MySQLdb.connect(SETTINGS['db_arche_prod']['host'], SETTINGS['db_arche_prod']['user'], SETTINGS['db_arche_prod']['pass'], SETTINGS['db_arche_prod']['db'])
  cursor_lib = db_lib.cursor()
  cursor_lib.execute("SELECT name FROM arche_prod.mdl_quiz,arche_prod.mdl_quiz_attempts WHERE arche_prod.mdl_quiz.id = arche_prod.mdl_quiz_attempts.quiz AND arche_prod.mdl_quiz_attempts.id="+str(id_quiz)+";")
  res=cursor_lib.fetchone()
  return res[0]
  db_lib.close()

def sendXapiStatement(statement):
  credentials = base64.b64encode(SETTINGS['api']['username'] +':'+ SETTINGS['api']['password'])
  url = SETTINGS['api']['uri'] + "/xAPI/statements"
  headers = {
    "Authorization": "Basic "+ credentials,
    "X-Experience-API-Version": "1.0.0"
    }
  r = requests.post(url, headers=headers, json=statement)
  return r.text

def sendCaliperStatement(statement):
  url = SETTINGS['api']['uri'] + "/key/caliper"
  headers = {
    "Authorization": SETTINGS['api']['username']
    }
  r = requests.post(url, headers=headers, json=statement)
  return r.text



# -------- Connexions DB -------- #

#Connexion DB arche
db = MySQLdb.connect(SETTINGS['db_arche_prod']['host'], SETTINGS['db_arche_prod']['user'], SETTINGS['db_arche_prod']['pass'], SETTINGS['db_arche_prod']['db'])
cursor = db.cursor()

#Connexion DB logs
db_log = MySQLdb.connect(SETTINGS['db_arche_prod_log']['host'], SETTINGS['db_arche_prod_log']['user'], SETTINGS['db_arche_prod_log']['pass'], SETTINGS['db_arche_prod_log']['db'])
cursor_log = db_log.cursor()



# -------- Dictionnaires de correspondance -------- #

#Création d'un dictionnaire avec les id moodle et les logins UL
# {32L: 'giretti1u', 33L: 'ostiatti1u', 34L: 'pallucca1u', 35L: 'thiery27u', 24L: 'riviere8u'}
#  moodle_users[32] => giretti1u
cursor.execute("SELECT id,username FROM arche_prod.mdl_user WHERE deleted=0 AND username LIKE '%u';")
rows_users = cursor.fetchall()
moodle_users={}
for row_user in rows_users:
  moodle_users[row_user[0]] = row_user[1]

#Création d'un dictionnaire avec les id de cours moodle et leur nom
# {1L: 'ARCHE Universit\xc3\xa9 de Lorraine', 2L: 'Espace \xc3\xa9tudiants', 3L: 'Espace enseignants', 4L: 'Podcast Premier semestre'}
# moodle_courses[3] => Espace enseignants
cursor.execute("SELECT id,fullname FROM arche_prod.mdl_course;")
rows_courses = cursor.fetchall()
moodle_courses={}
for row_course in rows_courses:
  moodle_courses[row_course[0]] = row_course[1]


# -------- Programme principal -------- #

#Récupération des logs de la journée
cursor_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log LIMIT 10;")
#cursor_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log where component='mod_quiz' and action='submitted' LIMIT 50;")
#cursor_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log where eventname like '%assessable_submitted' LIMIT 30;")
#cursor_log.execute("SELECT userid,courseid,eventname,component,action,target,objecttable,objectid,timecreated FROM arche_prod_log.logstore_standard_log where eventname like '%course_module_viewed' LIMIT 30;")
rows_log = cursor_log.fetchall()

for row_log in rows_log:
  row_userid = row_log[0]
  row_courseid = row_log[1]
  row_eventname = row_log[2]
  row_component = row_log[3]
  row_action = row_log[4]
  row_target = row_log[5]
  row_objecttable = row_log[6]
  row_objectid = row_log[7]
  row_timecreated = row_log[8]
  #On vérifie s'il s'agit d'un utilisateur remonté dans le tableau moodle_users (étudiant non deleted)
  if row_userid in moodle_users:
    #print(row_log)
    #(25069L, 11813L, '\\mod_resource\\event\\course_module_viewed', 'mod_resource', 'viewed', 'resource', 301058L)

    #On récupère le titre du cours concerné (s'il est présent dans la base)
    if row_courseid in moodle_courses:
        titre_cours = moodle_courses[row_courseid]
    else:
        titre_cours = "Cours supprimé de la plateforme"

    #--------------------------
    # Visualisation d'un cours
    #--------------------------
    if row_eventname == "\core\event\course_viewed":
        print(moodle_users[row_userid] + " viewed course " + str(row_courseid) + " (" + titre_cours + ") at " + str(datetime.datetime.fromtimestamp(row_timecreated).strftime('%Y-%m-%d %H:%M:%S')))
        json = {
        "data":[
            {
            "context" : "http://purl.imsglobal.org/ctx/caliper/v1p1",
            "type" : "Event",
            "actor" : {
                "id" : moodle_users[row_userid],
                "type" : "Person"
            },
            "action" : "Viewed",
            "object" : {
                "id" : row_courseid,
                "type" : "CourseSection",
                "name" : titre_cours,
            },
            "group": {
                "id" : row_courseid,
                "type" : "CourseSection"
            },
            "eventTime" : datetime.datetime.fromtimestamp(row_timecreated).isoformat()
            }
        ],
        "sendTime": datetime.datetime.now().isoformat(),
        "sensor": "http://atom.univ-lorraine.fr/collections/Events/Moodle"
        }
        print json
        print "---------"
        print sendCaliperStatement(json)

    #--------------------------
    # Visualisation d'un module de cours
    #--------------------------
    elif row_target == "course_module" and row_action == "viewed":
        print(moodle_users[row_userid] + " viewed module " + row_component + " (" + getNomModuleFromId(row_objecttable,row_objectid) + ") in course " + str(row_courseid) + " (" + titre_cours + ") at " + str(datetime.datetime.fromtimestamp(row_timecreated).strftime('%Y-%m-%d %H:%M:%S')))
        json = {
        "data":[
            {
            "context" : "http://purl.imsglobal.org/ctx/caliper/v1p1",
            "type" : "Event",
            "actor" : {
                "id" : moodle_users[row_userid],
                "type" : "Person"
            },
            "action" : "Viewed",
            "object" : {
                "id" : row_objectid,
                "type" : "DigitalResource",
                "name" : getNomModuleFromId(row_objecttable,row_objectid),
                "description" : row_component,
            },
            "group": {
                "id" : row_courseid,
                "type" : "CourseSection"
            },
            "eventTime" : datetime.datetime.fromtimestamp(row_timecreated).isoformat()
            }
        ],
        "sendTime": datetime.datetime.now().isoformat(),
        "sensor": "http://atom.univ-lorraine.fr/collections/Events/Moodle"
        }
        print json
        print "---------"
        print sendCaliperStatement(json)


    #--------------------------
    # Dépôt d'un devoir
    #--------------------------
    elif row_eventname == "\mod_assign\event\\assessable_submitted":
        print(moodle_users[row_userid] + " depot devoir (" + getNomDevoirFromId(row_objectid) + ") in course " + str(row_courseid) + " (" + titre_cours + ") at " + str(datetime.datetime.fromtimestamp(row_timecreated).strftime('%Y-%m-%d %H:%M:%S')))
        json = {
        "data":[
            {
            "context" : "http://purl.imsglobal.org/ctx/caliper/v1p1",
            "type" : "Event",
            "actor" : {
                "id" : moodle_users[row_userid],
                "type" : "Person"
            },
            "action" : "Submitted",
            "object" : {
                "id" : row_objectid,
                "type" : "AssignableDigitalResource",
                "name" : getNomDevoirFromId(row_objectid),
            },
            "group": {
                "id" : row_courseid,
                "type" : "CourseSection"
            },
            "eventTime" : datetime.datetime.fromtimestamp(row_timecreated).isoformat()
            }
        ],
        "sendTime": datetime.datetime.now().isoformat(),
        "sensor": "http://atom.univ-lorraine.fr/collections/Events/Moodle"
        }
        print json
        print "---------"
        print sendCaliperStatement(json)

    #--------------------------
    # Soumission d'un test (quiz)
    #--------------------------
    elif row_component == "mod_quiz" and row_action == "submitted":
        print(moodle_users[row_userid] + " soumission test (" + getNomQuizFromId(row_objectid) + ") in course " + str(row_courseid) + " (" + titre_cours + ") at " + str(datetime.datetime.fromtimestamp(row_timecreated).strftime('%Y-%m-%d %H:%M:%S')))
        json = {
        "data":[
            {
            "context" : "http://purl.imsglobal.org/ctx/caliper/v1p1",
            "type" : "Event",
            "actor" : {
                "id" : moodle_users[row_userid],
                "type" : "Person"
            },
            "action" : "Submitted",
            "object" : {
                "id" : row_objectid,
                "type" : "Assessment",
                "name" : getNomQuizFromId(row_objectid),
            },
            "group": {
                "id" : row_courseid,
                "type" : "CourseSection"
            },
            "eventTime" : datetime.datetime.fromtimestamp(row_timecreated).isoformat()
            }
        ],
        "sendTime": datetime.datetime.now().isoformat(),
        "sensor": "http://atom.univ-lorraine.fr/collections/Events/Moodle"
        }
        print json
        print "---------"
        print sendCaliperStatement(json)


    else:
        print("Autre : " + moodle_users[row_userid] + " " + row_action + " " + row_target + " " + str(row_timecreated))

#Fermetures DB
db.close()
db_log.close()
