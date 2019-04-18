# OpenLRW scripts

<p align="center">
   <a href='https://www.python.org/dev/peps/pep-0008/'><img src="https://img.shields.io/badge/code%20style-pep8-brightgreen.svg?style=flat-square" alt="code style pep 8"></a>
   <img src="https://img.shields.io/github/license/xchopin/openlrw-scripts.svg?style=flat-square"> 
   <img src="https://scrutinizer-ci.com/g/xchopin/OpenLRW-scripts/badges/quality-score.png?b=master" alt="code quality score">
</p>

> OpenLRW scripts is a repository of different scripts used at [University of Lorraine](https://en.wikipedia.org/wiki/University_of_Lorraine) to populate the collections of the Apereo OpenLRW API. <br>
All these scripts are open-source so feel free to use them!


## I. Requirements

 - #### Python Scripts
    - [Python ≥ 2.7](https://www.python.org/downloads/)
    - [openlrw-python-api-client](https://github.com/Apereo-Learning-Analytics-Initiative/OpenLRW-python-api-client)
    - [python-ldap](#2-python-ldap)
    - [PyYAML](#3-pyyaml)
    - [MySQLdb](#4-MySQLdb)
    - [OpenLDAP](https://stackoverflow.com/a/4768467/7644126)
   
 - #### Logstash Scripts
    - [Logstash ≥ 2.4](https://www.elastic.co/fr/downloads/logstash) 

  - #### Bash Scripts
    - An UNIX Operating System 


## II. Get started
### A. Clone the repository
`$ git clone https://github.com/xchopin/openlrw-scripts`

### B. Create and edit the settings file
```bash 
$ cd OpenLRW-scripts/bootstrap
$ cp settings.yml.dist settings.yml ; vi settings.yml
```

### C. Install the Python libraries
> To get the libraries you will need to have [PIP package manager](https://pypi.python.org/pypi/pip)

- #### 1. Download and install PIP
   `$ wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py ; python /tmp/get-pip.py`

- #### 2. python-ldap
   `$ pip install python-ldap` 
   
- #### 3. PyYAML
   `$ pip install pyyaml` 
   
- #### 4. MySQLdb   
   `$ pip install mysqlclient`
 



## II. Sources used to import data
- LDAP
- Log files from [CAS applications](https://en.wikipedia.org/wiki/Central_Authentication_Service)
- [Moodle LMS](https://moodle.com/)
- CSV from Apogée [(a software for the French universities)](https://fr.wikipedia.org/wiki/Apog%C3%A9e_(logiciel))

 
## III. API
### A. Users (mongoUser collection)
 > This script will import the users by using the LDAP database and the CSV files; there are 2 arguments possible

|        Action        |                        Usage                       |    Sources Used    |                           Description                           |
|:--------------------:|:--------------------------------------------------:|:------------------:|:---------------------------------------------------------------:|
| Import all the users | `$ python collection/Users/import_users.py reset`  | LDAP, Apogée (CSV) |                Clear then populate the collection               |
|        Update        | `$ python collection/Users/import_users.py update` | LDAP, Apogée (CSV) | Add the new users to the collection (slower: checks duplicates) |
|                      |                                                    |                    |                                                                 |

### B. Caliper Events (mongoEvent collection)
#### 1. Add CAS authentications to the collection
 > This script will import the "logged-in" events (students only)  by using log files
 
- ##### For one log file
```bash
$ cd collections/Events/CAS/
$ cat /logs/cas_auth.log | /opt/logstash/bin/logstash --quiet -w10 -f authentication.conf
```  

- ##### Treating a plenty of log files (from a date to YESTERDAY)
```bash
$ cd collections/Events/CAS/
$ sh authentications.sh
```  

#### 2. Add Moodle events to the collection

 > Import events from a timestamp

 `$ python collection/Events/Moodle/import_events.py TIMESTAMP` 
 
 > Import events from a timestamp to another timestamp
 
  `$ python collection/Events/Moodle/import_events.py TIMESTAMP TIMESTAMP` 
  
 > Import the 24h last events from the temporary table (if you have one)
 
  `$ python collection/Events/Moodle/import_last_events.py TIMESTAMP TIMESTAMP` 
  
### C. LineItems (LineItems collection)

#### 1. Add Moodle lineitems

` $ python collection/LineItems/Moodle/import_lineitems.py `

## V. License
OpenLRW-scripts is made available under the terms of the [Educational Community License, Version 2.0 (ECL-2.0)](https://opensource.org/licenses/ECL-2.0).
