#!/bin/bash
#

. /opt/victronenergy/serial-starter/run-service.sh

# app=$(dirname $0)/dbus-smartmeter.py

# start -x -s $tty
app="python3 dbus-smartmeter.py"
args=" /dev/$tty"
start $args
