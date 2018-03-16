#!/usr/bin/python
# coding: utf-8

from distutils.version import LooseVersion

import ldap
import logging
import requests
import settings
import smtplib
import sys
from ldap.controls import SimplePagedResultsControl

logging.basicConfig(filename='log/user.log', level=logging.WARN)

# Check if we're using the Python "ldap" 2.4 or greater API
LDAP_24_API = LooseVersion(ldap.__version__) >= LooseVersion('2.4')


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
    length = 74
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

    if length - len(message) >= 0:
        number = length - len(message)
        for i in xrange(0, number / 2):
            first_half_message += " "
        second_half_message = first_half_message
        if number % 2 != 0:
            second_half_message = first_half_message + " "

    print("""
╭──────────────────────────────────────────────────────────────────────────╮ 
│    OpenLRW  scripts    │             \033[31mERROR MESSAGE\033[0m                 ░▒▓▓▓▓│ 
├──────────────────────────────────────────────────────────────────────────│ 
│""" + first_half_reason + Colors.WARNING + reason + Colors.ENDC + second_half_reason + """│  
│""" + first_half_message + message + second_half_message + """│  
╰──────────────────────────────────────────────────────────────────────────╯
        """)


def generate_jwt():
    url = settings.api['uri'] + "/auth/login"
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    data = {"username": settings.api['username'], "password": settings.api['password']}

    try:
        r = requests.post(url, headers=headers, json=data)
        res = r.json()
        return res['token']
    except:
        mail = smtplib.SMTP('localhost')
        mail.sendmail(settings.mail['mfrom'], settings.mail['to'],
                      "Subject: Recuperation du JWT impossible \n\n Le script " +
                      sys.argv[0] + " ne peut pas récupérer un token auprès d'OpenLRW")
        sys.exit('Impossible de récupérer le JWT ')


def create_ldap_controls(page_size=settings.ldap['page_size']):
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


def set_ldap_cookie(lc_object, pctrls, pagesize=settings.ldap['page_size']):
    """Pushes the latest cookie back into the page control."""
    if LDAP_24_API:
        cookie = pctrls[0].cookie
        lc_object.cookie = cookie
        return cookie
    else:
        est, cookie = pctrls[0].controlValue
        lc_object.controlValue = (pagesize,cookie)
        return cookie
