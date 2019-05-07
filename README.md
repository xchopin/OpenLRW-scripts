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
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-LDAP-blue.svg?style=flat-square" alt="sources used">
</p>

- ##### Import all the users (populate)
This script will import the users by using the LDAP database.

> Clear then populate the collection (recommended for a new OpenLRW instance)

```
$ python collections/Users/LDAP/import_users.py reset
```

- ##### Update the collection
> Add the new users to the collection (slower: checks duplicates)

```
$ python collections/Users/LDAP/import_users.py update
```

<br>

#### - Add High school diploma (Baccalaureat) to students
<p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-.csv file (Apogée)-blue.svg?style=flat-square" alt="sources used">
</p>

⚠ **Your source file has to be located at `data/Users/baccalaureat_student.csv`.**


##### Sample of baccalaureat_student.csv

```csv
COD_ETU;COD_BAC;ANNEE_BAC;MNB_BAC
foobar1;S;2013;AB
foobar2;ES;2018;AB
foobar3;S;2012;
```

> The new informations will be added into the `metadata` attribute.

```
$ python collections/Users/Apogee/update_baccalaureat.py
```

<hr>

### 2. Events
#### - CAS Authentications
 <p align="center">
   <img src="https://img.shields.io/badge/language-Bash and Logstash-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-Log files (CAS)-blue.svg?style=flat-square" alt="sources used">
</p>
 
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


#### - Moodle LMS
<p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>

- ##### Import all the events

 > From a timestamp
 
 ```
 $ python collections/Events/Moodle/import_events.py TIMESTAMP
 ```  
 
 > From a timestamp to another one
 
 ```
 $ python collections/Events/Moodle/import_events.py TIMESTAMP TIMESTAMP
 ``` 
 
- ##### Import the events from the 24 last hours

> It queries a temporary table that contains the events oF the 24 last hours.

```
$ python collections/Events/Moodle/import_last_events.py
```
  
  
 <hr>
 
 
### 3. Class
#### - Moodle LMS
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>
 
 This script imports the Moodle classes, it also checks duplicates so you can run it several times for updates. <br>
 It also uses a .txt file to allow you to active the class you want (other will be inactive).
 
 ⚠ **The template file is located at `data/Classes/active_classes.txt.dist`.**
 
##### Copy the template file
```bash
$ cp data/Classes/active_classes.txt.dist data/Classes/active_classes.txt
```   
Then add the class id (one per line), you can add comments with the # character. <br>
In order to set all your classes as active just let the file empty.
   
##### Import classes from Moodle
```bash
$ python collections/Classes/Moodle/import_classes.py
```  

  <hr>
 
### 4. Result
#### - Moodle LMS
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>
 
This script imports the `Quizzes`, `Active quizzes` and the `Grades` from the Moodle database. Checking method is used for HTTP Post so you can use the script for populating and updating your collection.
 
##### Import results from Moodle
```bash
$ python collections/Results/Moodle/import_results.py
```  

#### - Apogée
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-.csv files (Apogée)-blue.svg?style=flat-square" alt="sources used">
</p>
 
 
##### Import results from Apogée

⚠ **Two files are required**
   - **the first one has to be located at `data/Results/apogee_results.csv` (it contains all the results)**
   - **the second has to be located at `data/Results/name.csv` (it contains the LineItem id and then the name of this LineItem** 
   
 ##### Sample of apogee_results.csv
 
 ```csv
foobar1;2019;3WLAEIMIA;200;initiale;1WIN12;800;UE1-AAAAA1-17.0-ADM
foobar2;2019;3WLAEIMIA;200;initiale;1WIN12;800;UE1-AAAAA1-12.0-ADM
foobar2;2019;3WLOEIMIA;200;initiale;1WIN12;800;UE1-AAAAA3-12.0-null
```   

 ##### Sample of name.csv
 
 ```csv
COD_ELP;LIB_ELP
AAAAA1;Discret Math
AAAAA2;Web applications with JavaEE
AAAAA3;Management
AAAAA4;Internship
```  
   
> Add the results by checking duplicates. It will add LineItem objects if they don't exist. In order to link these new LineItems to a Moodle class you will have a to use a script (more details in LineItems section)

```bash
$ python collections/Results/Apogee/import_results.py
```   
 
<hr>


### 5. LineItem
#### - Moodle LMS
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>
 
This script imports the lineItems from Moodle and also checks duplicates, it means you can use it several times for updates. 

> Import the LineItems
```bash
$ python collections/LineItems/Moodle/import_lineitems.py
```  

#### - Apogée
<p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-.csv files (Apogée)-blue.svg?style=flat-square" alt="sources used">
</p>
 
This script maps the LineItem objects created by the `import_results.py` script. For each Moodle class that contains the `classCode` key in `metadata` it checks if it equals their sourcedId.

> Map the Apogée LineItems to Moodle classes
```bash
$ python collections/LineItems/Apogee/
```  

 <hr>


### 6. Enrollments
#### - Moodle LMS
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>
 
This script imports the enrollments from Moodle with a timestamp argument (from)

> Import the Enrollments
```bash
$ python collections/Enrollments/Moodle/import_enrollments.py TIMESTAMP
```  


## V. License
OpenLRW-scripts is made available under the terms of the [Educational Community License, Version 2.0 (ECL-2.0)](https://opensource.org/licenses/ECL-2.0).
