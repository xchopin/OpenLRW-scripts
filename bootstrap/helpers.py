#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2018, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.0"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

from distutils.version import LooseVersion

import ldap
import logging
import requests
import yaml
import smtplib
import sys
import os
import base64
import time
from ldap.controls import SimplePagedResultsControl


# Check if we're using the Python "ldap" 2.4 or greater API
LDAP_24_API = LooseVersion(ldap.__version__) >= LooseVersion('2.4')

with open(os.path.dirname(__file__) + "/settings.yml", 'r') as dot_yml:
    SETTINGS = yaml.load(dot_yml)

API_URI = SETTINGS['api']['uri']
API_USERNAME = SETTINGS['api']['username']
API_PASSWORD = SETTINGS['api']['password']
TIME_START = time.time()


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def pretty_error(reason, message):
    length = 80
    first_half_reason = ""
    second_half_reason = ""
    first_half_message = ""
    second_half_message = ""

    if length - len(reason) >= 0:
        number = length - len(reason)
        for i in xrange(0, number/2):
            first_half_reason += " "
        second_half_reason = first_half_reason
        if number % 2 != 0:
            second_half_reason = first_half_reason + " "
    reason = first_half_reason + Colors.WARNING + reason + Colors.ENDC + second_half_reason
    if isinstance(message, list):
        message_line = ''
        for i in range(0, len(message)):
            msg = message[i]
            if length - len(msg) >= 0:
                number = length - len(msg)
                for j in xrange(0, number / 2):
                    first_half_message += " "
                second_half_message = first_half_message
                if number % 2 != 0:
                    second_half_message = first_half_message + " "
            message_line += "│" + first_half_message + msg + second_half_message + '│'
            if i is not len(message)-1:
                message_line += '\n'
    else:
        if length - len(message) >= 0:
            number = length - len(message)
            for i in xrange(0, number / 2):
                first_half_message += " "
            second_half_message = first_half_message
            if number % 2 != 0:
                second_half_message = first_half_message + " "
        message_line = "│" + first_half_message + message + second_half_message + "│"

    print("""
╭────────────────────────────────────────────────────────────────────────────────╮ 
│      OpenLRW scripts      │               \033[31mERROR MESSAGE\033[0m                  ░▒▓▓▓▓│ 
├────────────────────────────────────────────────────────────────────────────────│ 
│""" + reason + """│  
""" + message_line + """
╰────────────────────────────────────────────────────────────────────────────────╯
        """)
    sys.exit(1)


def pretty_message(reason, message):
    length = 80
    first_half_reason = ""
    second_half_reason = ""
    first_half_message = ""
    second_half_message = ""

    if length - len(reason) >= 0:
        number = length - len(reason)
        for i in xrange(0, number/2):
            first_half_reason += " "
        second_half_reason = first_half_reason
        if number % 2 != 0:
            second_half_reason = first_half_reason + " "
    reason = first_half_reason + Colors.WARNING + reason + Colors.ENDC + second_half_reason
    if isinstance(message, list):
        message_line = ''
        for i in range(0, len(message)):
            msg = message[i]
            if length - len(msg) >= 0:
                number = length - len(msg)
                for j in xrange(0, number / 2):
                    first_half_message += " "
                second_half_message = first_half_message
                if number % 2 != 0:
                    second_half_message = first_half_message + " "
            message_line += "│" + first_half_message + msg + second_half_message + '│'
            if i is not len(message)-1:
                message_line += '\n'
    else:
        if length - len(message) >= 0:
            number = length - len(message)
            for i in xrange(0, number / 2):
                first_half_message += " "
            second_half_message = first_half_message
            if number % 2 != 0:
                second_half_message = first_half_message + " "
        message_line = "│" + first_half_message + message + second_half_message + "│"

    print("""
╭────────────────────────────────────────────────────────────────────────────────╮ 
│        OpenLRW scripts        │                  """ + Colors.OKBLUE + """INFO\033[0m                    ░▒▓▓▓▓│ 
├────────────────────────────────────────────────────────────────────────────────│ 
│""" + reason + """│  
""" + message_line + """
╰────────────────────────────────────────────────────────────────────────────────╯
        """)


def generate_jwt():
    url = SETTINGS['api']['uri'] + "/api/auth/login"
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    data = {"username": SETTINGS['api']['username'], "password": SETTINGS['api']['password']}

    try:
        r = requests.post(url, headers=headers, json=data)
        res = r.json()
        return res['token']
    except:
        mail = smtplib.SMTP('localhost')
        mail.sendmail(SETTINGS['email']['from'], SETTINGS['email']['to'],
                      "Subject: Recuperation du JWT impossible \n\n Le script " +
                      sys.argv[0] + " ne peut pas récupérer un token auprès d'OpenLRW")
        sys.exit('Impossible de récupérer le JWT ')


def create_ldap_controls(page_size=SETTINGS['ldap']['page_size']):
    """Creates an LDAP control with a page size of "pagesize"."""
    # Initialize the LDAP controls for paging.
    # Note that we pass '' for the cookie because on first iteration, it starts out empty.
    if LDAP_24_API:
        return SimplePagedResultsControl(True, size=page_size, cookie='')
    else:
        return SimplePagedResultsControl(ldap.LDAP_CONTROL_PAGE_OID, True, (page_size, ''))


def get_ldap_controls(serverctrls):
    """Lookup an LDAP paged control object from the returned controls."""
    # Look through the returned controls and find the page controls.
    # This will also have our returned cookie which we need to make the next search request.
    if LDAP_24_API:
        return [c for c in serverctrls if c.controlType == SimplePagedResultsControl.controlType]
    else:
        return [c for c in serverctrls if c.controlType == ldap.LDAP_CONTROL_PAGE_OID]


def set_ldap_cookie(lc_object, pctrls, pagesize=SETTINGS['ldap']['page_size']):
    """Pushes the latest cookie back into the page control."""
    if LDAP_24_API:
        cookie = pctrls[0].cookie
        lc_object.cookie = cookie
        return cookie
    else:
        est, cookie = pctrls[0].controlValue
        lc_object.controlValue = (pagesize,cookie)
        return cookie


def send_xapi_statement(statement):
    """
    Helper function to send xAPI statements
    :param statement: JSON Object following the xAPI format
    :return: HTTP Status
    """
    credentials = base64.b64encode(API_USERNAME +':'+ API_PASSWORD)
    response = requests.post(API_URI + "/xAPI/statements", headers={"Authorization": "Basic "+ credentials, "X-Experience-API-Version": "1.0.0"}, json=statement)
    print(Colors.OKBLUE + '[POST]' + Colors.ENDC + ' /xAPI/statements - Response: ' + str(response.status_code))
    return response.status_code == 200


def send_caliper_statement(statement):
    """
    Helper function to send Caliper IMS statement
    :param statement:
    :return: HTTP Status
    """
    response = requests.post(API_URI + "/key/caliper", headers={"Authorization": API_USERNAME}, json=statement)
    print(Colors.OKBLUE + '[POST]' + Colors.ENDC + ' /key/caliper - Response: ' + str(response.status_code))
    return response.status_code


def measure_time():
    return str(time.time() - TIME_START)
