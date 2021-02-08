#!/usr/bin/env bash
# Author: Foster Hangdaan

# Sanity checks
if [[ $UID -ne 0 ]] ; then
  echo 'You must be root to run this script. Do you even sudo, bro?'
  exit 1
fi

# VARIABLES
DATADIR="/srv/blynk"
PROGDIR="/opt/blynk"
SYSCONF=$(realpath "blynk.service")

# Create Directories
if [[ ! -d $DATADIR ]] ; then
  mkdir -p $DATADIR
  chown pi:pi $DATADIR
fi
if [[ ! -d $PROGDIR ]] ; then
  mkdir -p $PROGDIR
  chown pi:pi $PROGDIR
else
  rm -rf ${PROGDIR}/*.jar*
fi

# Install Java
echo -n "Checking for openjdk... "
if [[ $(apt list --installed "openjdk*" 2>/dev/null | wc -l) -gt 1 ]] ; then
  echo "Openjdk already installed. Skipping installation."
else
  echo 'None found. Installing.'
  apt-get update && apt-get -y install openjdk-8-jdk openjdk-8-jre
fi

echo -n "Downloading Blynk JAR... "
cd $PROGDIR \
  && wget --quiet "https://github.com/blynkkk/blynk-server/releases/download/v0.41.13/server-0.41.13-java8.jar" \
  && echo 'Success'
  || { echo 'Failed' ; exit 1 ; }

#TODO: Install systemd file for Blynk Service
echo -n 'Copying systemd configuration... '
cp $SYSCONF /etc/systemd/system \
  && systemctl daemon-reload \
  && systemctl enable blynk \
  && systemctl start blynk \
  && echo 'Success' \
  || echo 'Failed'

if [[ $? -eq 0 ]] ; then
  echo "Blynk data is located at: $DATADIR"
  echo "Blynk jar is located at: $PROGDIR"
  echo 'To check the status, enter the following command: systemctl status blynk'
  echo 'Installation complete. Blynk server should be running on startup.'
else
  echo 'An error occured. Please contact emergency personnel.'
fi
