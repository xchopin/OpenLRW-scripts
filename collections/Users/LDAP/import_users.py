#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.5"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

import json
import sys, os

sys.path.append(os.path.dirname(__file__) + '/../../..')
from bootstrap.helpers import *

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                    filename=os.path.dirname(__file__) + '/users.log', level=logging.DEBUG)

parser = OpenLRW.parser
parser.add_argument('-r', '--reset', action='store_true', help='Clear the User collection and re-import all the users.')
parser.add_argument('-u', '--update', action='store_true', help='Add new LDAP users to the User collection')
parser.add_argument('--restore', action='store_true', help='Reset the data for each user + import the new users')
option = OpenLRW.enable_argparse()

# -------------- GLOBAL --------------
BASEDN = SETTINGS['ldap']['base_dn']
FILTER = SETTINGS['ldap']['filter']
ATTRLIST = ['uid', 'displayName']
COUNTER = 0


def diff(first, second):
    """
    compute the difference between two lists
    """
    second = set(second)
    return [item for item in first if item not in second]


def populate(check, jwt):
    """
     Populates the MongoUser collection by inserting all the LDAP users
    :param check: boolean to check duplicates
    :param jwt: JSON Web Token for OpenLRW
    :return: void
    """
    counter = 0
    OpenLRW.pretty_message('Initializing', 'Will soon populate the mongoUser collection')
    controls = create_ldap_controls(SETTINGS['ldap']['page_size'])
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

            data = {
                'status': 'active',
                'sourcedId': attributes['uid'][0],
                'givenName': attributes['displayName'][0],
                'enabledUser': True,
                'metadata': {}
            }

            try:
                OpenLrw.post_user(data, jwt, check)
            except ExpiredTokenException:
                jwt = OpenLrw.generate_jwt()
                OpenLrw.post_user(data, jwt, check)
            counter = counter + 1

        # Get cookie for next request
        pctrls = get_ldap_controls(server_ctrls)
        if not pctrls:
            print >> sys.stderr, 'Warning: Server ignores RFC 2696 control.'
            break

        cookie = set_ldap_cookie(controls, pctrls, SETTINGS['ldap']['page_size'])
        if not cookie:
            break
    l.unbind()

    return counter


def add_new_users_only(jwt):
    """
    Add only the new users that are not yet in the database
    """

    OpenLRW.pretty_message('Initializing', 'Updating the mongoUser collection')

    # First, we get all the users from the database
    users = json.loads(OpenLrw.get_users(jwt))
    db_users = []

    # Create an array of uids
    for user in users:
        uid = user['user']['sourcedId']
        db_users.append(uid)

    ldap_users = {}
    temp = []
    counter = 0
    controls = create_ldap_controls(SETTINGS['ldap']['page_size'])

    while 1:
        try:
            # Adjusting the scope such as SUBTREE can reduce the performance if you don't need it
            users = l.search_ext(BASEDN, ldap.SCOPE_ONELEVEL, FILTER, ATTRLIST, serverctrls=[controls])
        except ldap.LDAPError as e:
            OpenLRW.pretty_error('LDAP search failed', '%s' % e)

        try:
            rtype, rdata, ruser, server_ctrls = l.result3(users)  # Pull the results from the search request
        except ldap.LDAPError as e:
            OpenLRW.pretty_error('Couldn\'t pull LDAP results', '%s' % e)

        # treat the tuples gotten
        for dn, attributes in rdata:
            sourcedId = attributes['uid'][0]
            givenName = attributes['displayName'][0]
            temp.append(sourcedId)
            ldap_users[sourcedId] = givenName

        # Get cookie for next request
        pctrls = get_ldap_controls(server_ctrls)
        if not pctrls:
            print(sys.stderr, 'Warning: Server ignores RFC 2696 control.')
            break

        cookie = set_ldap_cookie(controls, pctrls, SETTINGS['ldap']['page_size'])
        if not cookie:
            break
    l.unbind()

    # Get the difference of old/new users
    new_users = diff(temp, db_users)

    # Send the users
    for user in new_users:
        data = {
            'status': 'active',
            'sourcedId': user,
            'enabledUser': True,
            'givenName': ldap_users[user],
            'metadata': {}
        }

        try:
            OpenLrw.post_user(data, jwt, False)
        except ExpiredTokenException:
            jwt = OpenLrw.generate_jwt()
            OpenLrw.post_user(data, jwt, False)
        counter = counter + 1

    return counter


# -------------- MAIN --------------
try:
    try:
        ldap.set_option(ldap.OPT_REFERRALS, 0)  # Don't follow referrals
        # Ignores server side certificate errors (assumes using LDAPS and self-signed cert).
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        l = ldap.initialize(SETTINGS['ldap']['host'] + ':' + SETTINGS['ldap']['port'])
        l.protocol_version = ldap.VERSION3  # Paged results only apply to LDAP v3
    except ldap.LDAPError as e:
        OpenLrw.mail_server(str(sys.argv[0]) + ' error', repr(e))
        OpenLRW.pretty_error("Unable to contact to the LDAP host", "Check the settings.py file")

    try:
        l.simple_bind_s(SETTINGS['ldap']['user'], SETTINGS['ldap']['password'])
    except ldap.LDAPError as e:
        OpenLrw.mail_server(str(sys.argv[0]) + ' error', repr(e))
        OpenLRW.pretty_error('LDAP bind failed', '%s' % e)

    jwt = OpenLrw.generate_jwt()

    if option.reset is True:  # Delete evey users and insert them
        users = OpenLrw.get_users(jwt)
        if users:
            data = json.loads(users)
            for row in data:
                try:
                    OpenLrw.delete_user(row['user']['sourcedId'], jwt)
                except OpenLRWClientException:
                    jwt = OpenLrw.generate_jwt()
                    OpenLrw.delete_user(row['user']['sourcedId'], jwt)
        else:
            OpenLRW.pretty_error('Can\'t get a JWT', 'Getting a JWT returns a 401 HTTP Error !')

        COUNTER = populate(False, jwt)
    elif option.update is True:
        COUNTER = add_new_users_only(jwt)
    elif option.restore is True:
        COUNTER = populate(True, jwt)
    else:
        OpenLRW.pretty_error("Wrong usage", "Run --help for more information")

    OpenLRW.pretty_message("Script finished", "Total number of users imported : " + str(COUNTER))

    message = str("LDAP Users imported (" + str(sys.argv[1]) + " method) in " + measure_time() + " seconds \n \n Total number of users imported : " + str(COUNTER))

    # OpenLrw.mail_server(str(sys.argv[0]) + " executed", message)
    logging.info(message)
    sys.exit(0)
except Exception as e:
    print(repr(e))
    OpenLrw.mail_server(str(sys.argv[0]) + ' error', repr(e))
    logging.error(repr(e))
    exit()
