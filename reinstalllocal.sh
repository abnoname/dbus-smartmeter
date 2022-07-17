#!/bin/sh

DRIVER=/opt/victronenergy/dbus-smartmeter
RUN=/opt/victronenergy/service-templates/dbus-smartmeter
OLD=/opt/victronenergy/service/dbus-smartmeter
if [ -d "$DRIVER" ]; then
  if [ -L "$DRIVER" ]; then
    # Remove old SymLink.
    rm "$DRIVER"
    # Create as folder
    mkdir "$DRIVER"
  fi
else
  # Create folder
  mkdir "$DRIVER"
fi
if [ -d "$RUN" ]; then
  if [ -L "$RUN" ]; then
    # Remove old SymLink.
    rm "$RUN"
    # Create as folder
    mkdir "$RUN"
  fi
else
  # Create folder
  mkdir "$RUN"
fi
if [ -d "$OLD" ]; then
  if [ -L "$OLD" ]; then
    # Remove old SymLink.
    rm "$RUN"
  fi
fi

cp -f /data/etc/dbus-smartmeter/* /opt/victronenergy/dbus-smartmeter
cp -rf /data/etc/dbus-smartmeter/service/* /opt/victronenergy/service-templates/dbus-smartmeter
