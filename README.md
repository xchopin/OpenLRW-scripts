# OpenLRW scripts
> These scripts are used to populate the Apero OpenLRW API by using different sources 

## Requirements
 - [OpenLRW](https://github.com/Apereo-Learning-Analytics-Initiative/OpenLRW)
 - [Python](https://www.python.org/downloads/)
 - [python-ldap](#get-python-ldap-library)
 - [OpenLDAP](https://stackoverflow.com/a/4768467/7644126)

## Sources used to import data
- LDAP
- Apogée [(a software for the French universities)](https://fr.wikipedia.org/wiki/Apog%C3%A9e_(logiciel))


## Tips
### Get python-ldap library
> To get this library you will need to have [PIP package manager](https://pypi.python.org/pypi/pip)

#### Download and install PIP
   `$ wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py ; python /tmp/get-pip.py`

#### Install python-ldap
   `$ pip install python-ldap` 
    