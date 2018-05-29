# OpenLRW scripts

OpenLRW-scripts is a repository where you can find scripts to populate the Apero OpenLRW API by using different sources. These scripts are used at the [University of Lorraine](https://en.wikipedia.org/wiki/University_of_Lorraine) and are open-source.

## I. Requirements
 - [OpenLRW](https://github.com/Apereo-Learning-Analytics-Initiative/OpenLRW)
 - [Logstash](https://www.elastic.co/fr/downloads/logstash) (≥ 2.4)
 - [Python](https://www.python.org/downloads/)
    - [python-ldap](#1-python-ldap)
    - [PyYAML](#2-pyyaml)
    - [OpenLDAP](https://stackoverflow.com/a/4768467/7644126)

## II. Sources used to import data
- CSV from Apogée [(a software for the French universities)](https://fr.wikipedia.org/wiki/Apog%C3%A9e_(logiciel))
- LDAP
- Log files from [CAS applications](https://en.wikipedia.org/wiki/Central_Authentication_Service)


## III. Get started
### A. Clone the repository
`$ git clone https://github.com/xchopin/OpenLRW-scripts.git`

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
 

## IV. Usage
### A. Add users to the mongoUser collection
 > This script will import the users by using the LDAP database and the CSV files; there are 2 arguments possible

- #### 1. Populate the collection
    > Clears then populates the collection (faster)

    `$ python users.py reset`    


- #### 2. Update the collection
    > Adds the new users to the collection (slower: checks duplicates)

    `$ python users.py update`  

### B. Add CAS authentications to the mongoEvent collection
 > This script will import the "logged-in" events (students only)  by using log files
 
- #### 1. For one log file
```bash
$ cat /logs/cas_auth.log | /opt/logstash/bin/logstash --quiet -w10 -f xapi_cas.conf
```  

- #### 2. Treating a plenty of log files (from a date to YESTERDAY)
```bash
$ cd collections/Events/
$ sh cas_authentications.sh
```  

## V. License
OpenLRW-scripts is made available under the terms of the [Educational Community License, Version 2.0 (ECL-2.0)](https://opensource.org/licenses/ECL-2.0).
