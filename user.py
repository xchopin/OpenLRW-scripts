#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import requests, json
from bootstrap.helpers import *
from bootstrap import settings


logging.basicConfig(filename='log/user.log', level=logging.WARN)


# -------------- GLOBAL --------------
BASEDN = settings.ldap['base_dn']
ATTRLIST = ['uid', 'displayName', 'businessCategory', 'eduPersonPrincipalName']


# -------------- FUNCTIONS --------------
def post_user(jwt, data, check):
    check = 'false' if check is False else 'true'
    response = requests.post(settings.api['uri'] + '/users?check=' + check, headers={'Authorization': 'Bearer ' + jwt}, json=data)
    return response.status_code == 401  # if token expired


def get_users(jwt):
    response = requests.get(settings.api['uri'] + '/users', headers={'Authorization': 'Bearer ' + jwt})
    return False if response.status_code == 401 else response.content  # if token expired


def delete_user(jwt, user_id):
    response = requests.delete(settings.api['uri'] + '/users/' + user_id, headers={'Authorization': 'Bearer ' + jwt})
    return response.status_code == 401  # if token expired


def populate(check, jwt):
    """
     Populates the MongoUser collection by inserting all the LDAP users
    :param check: boolean to check duplicates
    :param jwt: JSON Web Token for OpenLRW
    :return: void
    """
    controls = create_ldap_controls(settings.ldap['page_size'])
    while 1 < 2:  # hi deadmau5
        try:
            # Adjusting the scope such as SUBTREE can reduce the performance if you don't need it
            users = l.search_ext(BASEDN, ldap.SCOPE_ONELEVEL, 'uid=*', ATTRLIST, serverctrls=[controls])
        except ldap.LDAPError as e:
            pretty_error('LDAP search failed', '%s' % e)

        try:
            rtype, rdata, ruser, server_ctrls = l.result3(users)  # Pull the results from the search request
        except ldap.LDAPError as e:
            pretty_error('Couldn\'t pull LDAP results', '%s' % e)

        for dn, attributes in rdata:
            json = {
                'sourcedId': attributes['uid'][0],
                'givenName': attributes['displayName'][0],
                'metadata': {
                    'ldap_business_category': attributes['businessCategory'][0]
                }
            }

            if not post_user(jwt, json, check):
                jwt = generate_jwt()
                post_user(jwt, json, check)

        # Get cookie for next request
        pctrls = get_ldap_controls(server_ctrls)
        if not pctrls:
            print >> sys.stderr, 'Warning: Server ignores RFC 2696 control.'
            break

        cookie = set_ldap_cookie(controls, pctrls, settings.ldap['page_size'])
        if not cookie:
            break
    l.unbind()


# -------------- MAIN --------------
# Checking args
if not (len(sys.argv) == 2 and (sys.argv[1] == 'reset' or sys.argv[1] == 'update')):
    pretty_error(
        "Wrong usage",
        ["reset: clears the user collection then imports them without checking duplicates", "update: imports new users"]
    )

try:
    ldap.set_option(ldap.OPT_REFERRALS, 0)   # Don't follow referrals
    # Ignores server side certificate errors (assumes using LDAPS and self-signed cert).
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    l = ldap.initialize(settings.ldap['host'] + ':' + settings.ldap['port'])
    l.protocol_version = ldap.VERSION3  # Paged results only apply to LDAP v3
except ldap.LDAPError, e:
    pretty_error("Unable to contact to the LDAP host", "Check the settings.py file")

try:
    l.simple_bind_s(settings.ldap['user'], settings.ldap['password'])
except ldap.LDAPError as e:
    pretty_error('LDAP bind failed', '%s' % e)

jwt = generate_jwt()

if sys.argv[1] == 'reset':  # Deletes evey users and inserts them
    users = get_users(jwt)
    if users:  # It shouldn't expire but it's better to check
        data = json.loads(users)
        for row in data:
            if not delete_user(jwt, row['user']['sourcedId']):
                jwt = generate_jwt()
                delete_user(jwt, row['user']['sourcedId'])
    else:
        pretty_error('Can\'t get a JWT', 'Getting a JWT returns a 401 HTTP Error !')
    populate(False, jwt)
elif sys.argv[1] == 'update':
    populate(True, jwt)

sys.exit(0)