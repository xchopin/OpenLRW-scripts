# OpenLRW scripts

<p align="center">
   <a href='https://www.python.org/dev/peps/pep-0008/'><img src="https://img.shields.io/badge/code%20style-pep8-brightgreen.svg?style=flat-square" alt="code style pep 8"></a>
   <img src="https://img.shields.io/github/license/xchopin/openlrw-scripts.svg?style=flat-square"> 
   <img src="https://scrutinizer-ci.com/g/xchopin/OpenLRW-scripts/badges/quality-score.png?b=master" alt="code quality score">
</p>

**This is a repository of different scripts used at [University of Lorraine](https://en.wikipedia.org/wiki/University_of_Lorraine) to populate the collections of the OpenLRW API. 
<br> <br>
All these scripts are open-source, so feel free to edit/use them!**


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

## II. Get started
### 1. Clone the repository
```
$ git clone https://github.com/xchopin/openlrw-scripts
```

### 2. Create and edit the settings file
```bash 
$ cd OpenLRW-scripts/bootstrap
$ cp settings.yml.dist settings.yml ; vi settings.yml
```

### 3. Install the Python libraries
> To get the libraries you will need to have [PIP package manager](https://pypi.python.org/pypi/pip)

- #### A. Download and install PIP
   ```
   $ wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py ; python /tmp/get-pip.py
   ```

- #### B. python-ldap
   ```
   $ pip install python-ldap
   ``` 
   
- #### C. PyYAML
   ```
   $ pip install pyyaml
   ```
   
- #### D. MySQLdb   
   ```
   $ pip install mysqlclient
   ```
 
 
## III. Usage
### 1. Users
#### - Import users
<img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used"> <img src="https://img.shields.io/badge/sources used-LDAP-blue.svg?style=flat-square" alt="sources used">
- ##### Import all the users (populate)
This script will import the users by using the LDAP database.

> Clear then populate the collection (recommended for a new OpenLRW instance)

```
$ python collection/Users/LDAP/import_users.py reset
```

- ##### Update the collection
> Add the new users to the collection (slower: checks duplicates)

```
$ python collection/Users/LDAP/import_users.py update
```

#### - Add High school diploma (Baccalaureat) to students
> Language: Python - Sources used: .csv file (users data from Apogée)

⚠ **Your source file has to be located at this place `data/Users/baccalaureat_student.csv`.**

> The new informations will be added into the metadata attribute.

```
$ python collection/Users/Apogee/update_baccalaureat.py
```

<hr>

### 2. Events
#### - CAS Authentications
 <img src="https://img.shields.io/badge/language-Bash and Logstash-brightgreen.svg?style=flat-square" alt="language used"> <img src="https://img.shields.io/badge/sources used-Log files (CAS)-blue.svg?style=flat-square" alt="sources used">
 
 This script will import the "logged-in" events (students only)  by using log files
    
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

<hr>

#### - Moodle LMS
<img src="https://img.shields.io/badge/language-python-brightgreen.svg?style=flat-square" alt="language used"> <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">

- ##### Import all the events

 > From a timestamp
 
 ```
 $ python collection/Events/Moodle/import_events.py TIMESTAMP
 ```  
 
 > From a timestamp to another one
 
 ```
 $ python collection/Events/Moodle/import_events.py TIMESTAMP TIMESTAMP
 ``` 
  
- ##### Import the events from the 24 last hours
  > It queries a temporary table that contains the events on the 24 last hours.

```$ python collection/Events/Moodle/import_last_events.py```
  
  
  
  
  
### C. LineItems (LineItems collection)

#### 1. Add Moodle lineitems

` $ python collection/LineItems/Moodle/import_lineitems.py `

## V. License
OpenLRW-scripts is made available under the terms of the [Educational Community License, Version 2.0 (ECL-2.0)](https://opensource.org/licenses/ECL-2.0).
