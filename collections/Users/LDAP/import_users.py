#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.1"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import json
import sys, os
sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(filename=os.path.dirname(__file__) + '/users.log', level=logging.DEBUG)

# -------------- GLOBAL --------------
BASEDN = SETTINGS['ldap']['base_dn']
FILTER = SETTINGS['ldap']['filter']
#ATTRLIST = ['uid', 'displayName', 'businessCategory', 'eduPersonPrincipalName']
ATTRLIST = ['uid', 'displayName']
COUNTER = 0

def populate(check, jwt):
    """
     Populates the MongoUser collection by inserting all the LDAP users
    :param check: boolean to check duplicates
    :param jwt: JSON Web Token for OpenLRW
    :return: void
    """
    OpenLRW.pretty_message('Initializing', 'Will soon populate the mongoUser collection')
    controls = create_ldap_controls(SETTINGS['ldap']['page_size'])
    COUNTER = 0
    while 1 < 2:  # hi deadmau5
        try:
            # Adjusting the scope such as SUBTREE can reduce the performance if you don't need it
            users = l.search_ext(BASEDN, ldap.SCOPE_ONELEVEL, FILTER, ATTRLIST, serverctrls=[controls])
        except ldap.LDAPError as e:
            OpenLRW.pretty_error('LDAP search failed', '%s' % e)

        try:
            rtype, rdata, ruser, server_ctrls = l.result3(users)  # Pull the results from the search request
        except ldap.LDAPError as e:
            OpenLRW.pretty_error('Couldn\'t pull LDAP results', '%s' % e)

        for dn, attributes in rdata:
            #if 'businessCategory' not in attributes:
            #    print attributes['uid'][0]
            #    continue

            json = {
                'sourcedId': attributes['uid'][0],
                'givenName': attributes['displayName'][0],
                'metadata' : {}
            }

            try:
                OpenLrw.post_user(json, jwt, check)
            except ExpiredTokenException:
                jwt = OpenLrw.generate_jwt()
                OpenLrw.post_user(json, jwt, check)
            COUNTER = COUNTER + 1
           
        # Get cookie for next request
        pctrls = get_ldap_controls(server_ctrls)
        if not pctrls:
            print >> sys.stderr, 'Warning: Server ignores RFC 2696 control.'
            break

        cookie = set_ldap_cookie(controls, pctrls, SETTINGS['ldap']['page_size'])
        if not cookie:
            break
    l.unbind()


# -------------- MAIN --------------
if not (len(sys.argv) == 2 and (sys.argv[1] == 'reset' or sys.argv[1] == 'update')):  # Checking args
    OpenLRW.pretty_error(
        "Wrong usage",
        ["reset: clears the user collection then imports them without checking duplicates", "update: imports new users"]
    )

try:
    ldap.set_option(ldap.OPT_REFERRALS, 0)   # Don't follow referrals
    # Ignores server side certificate errors (assumes using LDAPS and self-signed cert).
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    l = ldap.initialize(SETTINGS['ldap']['host'] + ':' + SETTINGS['ldap']['port'])
    l.protocol_version = ldap.VERSION3  # Paged results only apply to LDAP v3
except ldap.LDAPError as e:
    OpenLRW.pretty_error("Unable to contact to the LDAP host", "Check the settings.py file")

try:
    l.simple_bind_s(SETTINGS['ldap']['user'], SETTINGS['ldap']['password'])
except ldap.LDAPError as e:
    OpenLRW.pretty_error('LDAP bind failed', '%s' % e)

jwt = OpenLrw.generate_jwt()

if sys.argv[1] == 'reset':  # Deletes evey users and inserts them
    users = OpenLrw.get_users(jwt)
    if users:  # It shouldn't expire but it's better to check
        data = json.loads(users)
        for row in data:
            try:
                OpenLrw.delete_user(row['user']['sourcedId'], jwt)
            except OpenLRWClientException:
                jwt = OpenLrw.generate_jwt()
                OpenLrw.delete_user(row['user']['sourcedId'], jwt)
    else:
        OpenLRW.pretty_error('Can\'t get a JWT', 'Getting a JWT returns a 401 HTTP Error !')
    populate(False, jwt)
elif sys.argv[1] == 'update':
    populate(True, jwt)


OpenLRW.pretty_message("Script finished", "Total number of users imported : " + str(COUNTER))

message = str("LDAP Users imported in " + measure_time() + " seconds")

OpenLrw.mail_server(str(sys.argv[0]) + " summary", message)

sys.exit(0)
