# OpenLRW scripts

<p align="center">
   <a href='https://www.python.org/dev/peps/pep-0008/'><img src="https://img.shields.io/badge/code%20style-pep8-brightgreen.svg?style=flat-square" alt="code style pep 8"></a>
   <img src="https://img.shields.io/github/license/xchopin/openlrw-scripts.svg?style=flat-square"> 
   <img src="https://scrutinizer-ci.com/g/xchopin/OpenLRW-scripts/badges/quality-score.png?b=master" alt="code quality score">
</p>

**This is a repository of different scripts used at [University of Lorraine](https://en.wikipedia.org/wiki/University_of_Lorraine) to populate the collections of the OpenLRW API. 
<br> <br>
All these scripts are made for the Educational community, don't hesitate to contribute!**


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


## II. Table of contents
* [User](#1-user)
* [Event](#2-event)
* [Class](#3-class)
* [Result](#4-result)
* [LineItem](#5-lineitem)
* [Enrollment](#6-enrollment)



## III. Get started
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
   > :warning: This library requires [python-devel and openldap](https://stackoverflow.com/a/4768467/10408181)

   ```
   $ pip install python-ldap
   ``` 
   
- #### C. PyYAML
   ```
   $ pip install pyyaml
   ```
   
- #### D. MySQLdb  
   > :warning: This library requires mariadb-devel `yum install mariadb-devel`
   ```
   $ pip install mysqlclient
   ```
   
- #### E. OpenLRW  
   ```
   $ pip install openlrw
   ``` 
 
## IV. Usage
## Global flags
```
-v / --verbose : to print all the HTTP calls
-no-mail : to don't send any emails
-h / --help : help documentation

```

### 1. User
#### - Import users
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-LDAP-blue.svg?style=flat-square" alt="sources used">
</p>

- ##### Import all the users (populate)
This script will import the users by using the LDAP database.

> Clear then populate the collection (recommended for a new OpenLRW instance)

```
$ python collections/Users/LDAP/import_users.py --reset
```

- ##### Update the collection
> Add the new users to the collection

```
$ python collections/Users/LDAP/import_users.py --update
```

<br>

#### - Add their civic information
<p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-.csv file (Apogée)-blue.svg?style=flat-square" alt="sources used">
</p>


> The new information will be added into the `metadata` attribute of users.


- ##### Parse a file
```
$ python collections/Users/Apogee/import_civic_information.py --file path_to_your_file.csv
```

- ##### Parse the files containing the date of yesterday
> Aimed to a CRON use - Format: YYYYmmdd.csv - eg: Students_CS_20191030.csv; Students_Biology_20191030.csv 

⚠ **The repository of your source files has to be indicated in the settings file, at the  `civic_information_directory` attribute.**

   

```
$ python collections/Users/Apogee/import_civic_information.py --file path_to_your_file.csv
```


##### Sample of a civic information file

```csv
CMP;LOGIN;YEAR;GENDER;CHILDREN;HANDICAP;HAS_SCHOLARSHIP;HAS_A_JOB;HAS_ADAPTED_STUDY_PLAN;CITY;BACCALAUREAT_YEAR;BACCALAUREAT_TYPE;BACCALAUREAT_ZIPCODE;BACCALAUREAT_HONOR
AB0;foo;1998;F;0;null;N;O;N;PARIS;2018;ES;054;P
AB0;bar;2000;F;0;null;N;O;N;NANCY;2017;ES;054;AB
AB0;foobar;1991;M;0;null;N;N;O;LYON;2009;S;093;P
```

<hr>

### 2. Event
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
 $ python collections/Events/Moodle/import_events.py -t TIMESTAMP
 ```  
 
 > From a timestamp to another one
 
 ```
 $ python collections/Events/Moodle/import_events.py -t TIMESTAMP TIMESTAMP
 ``` 
 
- ##### Update the events

> Check the most recent event stored in the database and insert the newer ones

```
 $ python collections/Events/Moodle/import_events.py -u
```
  
  
 <hr>
 
 
### 3. Class
#### - Import from Moodle LMS
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>
 
 This script imports the Moodle classes, it uses a .txt file to allow you to active the class you want (other will be inactive).  <br>
 It also checks duplicates so you can run it several times for updates.
 
 ⚠ **The template file is located at `data/Classes/active_classes.txt.dist`.**
 
##### Copy the template file
```bash
$ cp data/Classes/active_classes.txt.dist data/Classes/active_classes.txt
```   
Then add the class id (one per line), you can add comments with the # character. <br>
In order to set all your classes as active just let the file empty.
   
##### Run the script
```bash
$ python collections/Classes/Moodle/import_classes.py
```  
#### - Clear the collection

<p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-None -blue.svg?style=flat-square" alt="sources used">
</p>

This script will clear the whole Class collection from MongoDB (it keeps the indices though), it performs only one HTTP DELETE request.

##### Run the script

```bash
$ python collections/Classes/delete_all_classes.py
```

  <hr>
 
### 4. Result
#### - Moodle LMS
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>
 
This script imports the `Quizzes`, `Active quizzes` and the `Grades` from the Moodle database. Checking method is used for HTTP Post so you can use the script for populating and updating your collection.
 
 
##### Import all the results from a timestamp
> The condition is made on Moodle's timemodified attribute

```bash
$ python collections/Results/Moodle/import_results.py --from TIMESTAMP
```  

##### Import all the results from a timestamp to another one
> The condition is made on Moodle's timemodified attribute

```bash
$ python collections/Results/Moodle/import_results.py --from TIMESTAMP --to TIMESTAMP
```  
##### Update the results
> Import only the results that are older to the last result in MongoDB
```bash
$ python collections/Results/Moodle/import_results.py -u
```  

#### - Apogée (SIS)
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-.csv files (Apogée)-blue.svg?style=flat-square" alt="sources used">
</p>
 
 
##### Import results from Apogée

> Import the results from an Apogée csv file; it also add LineItem objects if they don't exist. In order to link these new LineItems to a Moodle class you will have a to use a script (more details in LineItems section)

⚠ **Two field are required in the settings file**
   - **`results_directory` where you have to put files with the following format YYYYmmdd.csv eg: export1_20193010.csv**
   - **`lineitems_name_filepath` you have to indicate the absolute path of a csv file for the lineitems** 
  
###### Sample of a result file

 ```csv
foobar1;2019;3WLAEIMIA;200;initiale;1WIN12;800;UE1-AAAAA1-17.0-ADM
foobar2;2019;3WLAEIMIA;200;initiale;1WIN12;800;UE1-AAAAA1-12.0-ADM
foobar2;2019;3WLOEIMIA;200;initiale;1WIN12;800;UE1-AAAAA3-12.0-null
```   

###### Sample of a lineitems file

```csv
COD_ELP;LIB_ELP
AAAAA1;Discret Math
AAAAA2;Web applications with JavaEE
AAAAA3;Management
AAAAA4;Internship
```  
  
  
###### Import the results from the files containing 
> Import all the results from the files containing the date of yesterday
```bash
$ python collections/Results/Apogee/import_results.py -l
```        
  
  
###### Update the results
> Make a difference between the results of yesterday and the day before (for CRON)
```bash
$ python collections/Results/Apogee/import_results.py -u
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
 
This script maps the LineItem objects created by the `import_results.py` script. For each Moodle class that contains the `classCode` key in `metadata` it checks if it equals their sourcedId. Ita lso checks duplicates which means you can use it several times for updates. 

> Map the Apogée LineItems to Moodle classes
```bash
$ python collections/LineItems/Apogee/map_classes.py
```  

 <hr>


### 6. Enrollment
#### - Moodle LMS
 <p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-MySQL (Moodle)-blue.svg?style=flat-square" alt="sources used">
</p>
 
This script imports the enrollments from Moodle with a timestamp argument (from)

> Import the Enrollments
```bash
$ python collections/Enrollments/Moodle/import_enrollments.py --from TIMESTAMP
```  

> Update the Enrollments
```bash
$ python collections/Enrollments/Moodle/import_enrollments.py -u
```  

#### - Clear the collection

<p align="center">
   <img src="https://img.shields.io/badge/language-Python-brightgreen.svg?style=flat-square" alt="language used">
   <img src="https://img.shields.io/badge/sources used-None -blue.svg?style=flat-square" alt="sources used">
</p>

This script will clear the whole Enrollment collection from MongoDB (it keeps the indices though), it performs only one HTTP DELETE request.

##### Run the script

```bash
$ python collections/Enrollments/delete_all_enrollments.py
```


## V. License
OpenLRW-scripts is made available under the terms of the [Educational Community License, Version 2.0 (ECL-2.0)](https://opensource.org/licenses/ECL-2.0).
