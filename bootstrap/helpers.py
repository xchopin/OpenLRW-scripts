#!/usr/bin/python
# coding: utf-8

__author__ = "Xavier Chopin"
__copyright__ = "Copyright 2019, University of Lorraine"
__license__ = "ECL-2.0"
__version__ = "1.0.2"
__email__ = "xavier.chopin@univ-lorraine.fr"
__status__ = "Production"

from distutils.version import LooseVersion
from openlrw.client import OpenLRW
from openlrw.exceptions import *

import ldap
import yaml
import os
import time
import logging
from ldap.controls import SimplePagedResultsControl

# Check if we're using the Python "ldap" 2.4 or greater API
LDAP_24_API = LooseVersion(ldap.__version__) >= LooseVersion('2.4')

with open(os.path.dirname(__file__) + "/settings.yml", 'r') as dot_yml:
    SETTINGS = yaml.load(dot_yml)

API_URI = SETTINGS['api']['uri']
API_USERNAME = SETTINGS['api']['username']
API_PASSWORD = SETTINGS['api']['password']
OpenLrw = OpenLRW(API_URI, API_USERNAME, API_PASSWORD)
OpenLrw.setup_email('localhost', SETTINGS['email']['from'], SETTINGS['email']['to'])
TIMESTAMP_REGEX = r'^(\d{10})?$'

TIME_START = time.time()


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


def measure_time():
    return str(time.time() - TIME_START)
