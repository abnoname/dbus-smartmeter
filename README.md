# dbus-smartmeter Service
Project derived from https://github.com/RalfZim/venus.dbus-fronius-smartmeter

### Purpose

This service is meant to be run on a raspberry Pi with Venus OS from Victron.

The Python script cyclically reads data from the SML SmartMeter via serial port and publishes information on the dbus, using the service name com.victronenergy.grid. This makes the Venus OS work as if you had a physical Victron Grid Meter installed.

### Configuration

In the Python file, you should put the IP of your SML device that hosts the REST API. In my setup, it is the IP of the SML Symo, which gets the data from the SML Smart Metervia the RS485 connection between them.

### Installation

...
