#!/bin/bash
#title          :authentications.sh
#license        :ECL-2.0
#description    :This script will populate the mongodb Events collection by parsing all the log files from the date you enter to yesterday
#author         :Xavier Chopin <xavier.chopin@univ-lorraine.fr>
#date           :20180419
#version        :0.1
#usage          :sh authentications.sh
#notes          :This script is provided with the OpenLRW-scripts bundle therefore it requires Logstash > 2.4
#notes          :In this script log files are located in /data/logs/YEARMONTHDAY and files are compressed in .gz, log files are created by CAS Applications
#bash_version   :4.2.46(2)-release
#==============================================================================
LAST_DATE=$(date +%Y%m%d -d "yesterday")

echo "╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮"
echo -e "│  OpenLRW Scripts  │  This script will loop on every log files from the \e[36mdate you will enter \e[39mto \e[36m$LAST_DATE \e[39m  │"
echo "│__________________________________________________________________________________________________________│"
echo -e "│                           Please enter the first date to parse (YEARMONTHDAY)                            │"
echo "╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯"
echo -en "First Date: \e[92m"
read FIRST_DATE

if [ -d "/data/logs/${FIRST_DATE}" ]; then
     echo -e "\e[39mParsing..."
     CURSOR=$FIRST_DATE
     FILES=""
     while [ $CURSOR -le $LAST_DATE ]; do
            if [ -d "/data/logs/${CURSOR}" ]; then
                for filename in /data/logs/${CURSOR}/serviceStats.log.gz; do
                   FILES=$FILES" "$filename
                done
            fi
            CURSOR=$(date +%Y%m%d -d "$CURSOR + 1 day")
     done
     echo "Sending data to Logstash script..."
     zcat $FILES | /opt/logstash/bin/logstash --quiet -w30 -f cas_authentications.conf
else
	echo -e "\e[31mError: This folder does not exist\e[39m"
fi
