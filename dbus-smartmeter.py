#!/usr/bin/env python3
#
# Copyright (c) 2022 Franz Neumann
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Created by Ralf Zimmermann (mail@ralfzimmermann.de) in 2020.
This code and its documentation can be found on: https://github.com/RalfZim/venus.dbus-fronius-smartmeter
Used https://github.com/victronenergy/velib_python/blob/master/dbusdummyservice.py as basis for this self._dbusservice.
Reading information from the Fronius Smart Meter via http REST API and puts the info on dbus.
"""

import datetime
import logging
import os
import platform
import sys
import time
if sys.version_info.major == 2:
    import gobject
else:
    from gi.repository import GLib as gobject

# replace mmap module with sys (not needed and unavailable on venusos)
sys.modules["mmap"] = sys
from sml import SmlBase, SmlSequence

# Victron packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__),
                '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from settingsdevice import SettingsDevice
from vedbus import VeDbusService

from threading import Lock, Thread
from serial import Serial

path_UpdateIndex = '/UpdateIndex'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmlReader(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.dev = ""
        self.errorPower = 0
        self.running = True
        self.terminateOnTimeout = 0
        self.smlTimeoutSec = 5
        self.proto = SmlBase()
        self.lastUpdate = datetime.datetime.now()
        self.lock = Lock()
        self.meterData = {
            "energy_active": 0,
            "import_energy_active": 0,
            "power_active": 0,
            "l1_power_active": 0,
            "l2_power_active": 0,
            "l3_power_active": 0,
            "voltage_ln": 0,
            "l1n_voltage": 0,
            "l2n_voltage": 0,
            "l3n_voltage": 0,
            "voltage_ll": 0,
            "l12_voltage": 0,
            "l23_voltage": 0,
            "l31_voltage": 0,
            "frequency": 0,
            "l1_energy_active": 0,
            "l2_energy_active": 0,
            "l3_energy_active": 0,
            "l1_import_energy_active": 0,
            "l2_import_energy_active": 0,
            "l3_import_energy_active": 0,
            "export_energy_active": 0,
            "l1_export_energy_active": 0,
            "l2_export_energy_active": 0,
            "l3_export_energy_active": 0,
            "energy_reactive": 0,
            "l1_energy_reactive": 0,
            "l2_energy_reactive": 0,
            "l3_energy_reactive": 0,
            "energy_apparent": 0,
            "l1_energy_apparent": 0,
            "l2_energy_apparent": 0,
            "l3_energy_apparent": 0,
            "power_factor": 0,
            "l1_power_factor": 0,
            "l2_power_factor": 0,
            "l3_power_factor": 0,
            "power_reactive": 0,
            "l1_power_reactive": 0,
            "l2_power_reactive": 0,
            "l3_power_reactive": 0,
            "power_apparent": 0,
            "l1_power_apparent": 0,
            "l2_power_apparent": 0,
            "l3_power_apparent": 0,
            "l1_current": 0,
            "l2_current": 0,
            "l3_current": 0,
            "demand_power_active": 0,
            "minimum_demand_power_active": 0,
            "maximum_demand_power_active": 0,
            "demand_power_apparent": 0,
            "l1_demand_power_active": 0,
            "l2_demand_power_active": 0,
            "l3_demand_power_active": 0
        }
        self.meterDataZero = self.meterData.copy()

    def getMeterData(self):
        duration = (datetime.datetime.now() - self.lastUpdate)
        if(duration.seconds > self.smlTimeoutSec):
            self.lock.acquire()
            self.meterData = self.meterDataZero.copy()
            self.lock.release()
            if(self.terminateOnTimeout == 1):
                logger.error("meter data not within time. quit.")
                os._exit(1)
            else:
                logger.error("meter data not within time. resume.")
        return self.meterData

    def event(self, message_body: SmlSequence) -> None:
        for val in message_body.get('valList', []):
            if('1-0:1.8.0*255' in val["objName"]):
                self.meterData["import_energy_active"] = val["value"]
                self.meterData["l1_import_energy_active"] = val["value"] / 3.0
                self.meterData["l2_import_energy_active"] = val["value"] / 3.0
                self.meterData["l3_import_energy_active"] = val["value"] / 3.0
            if('1-0:16.7.0*255' in val["objName"]):
                if(val["value"] < 1):
                    if(self.errorPower > -1000):
                        self.errorPower = self.errorPower - 50
                else:
                    if(self.errorPower < 0):
                        self.errorPower = self.errorPower + 50
                if(self.errorPower < 0):
                    val["value"] = self.errorPower

                self.meterData["power_active"] = +1 * val["value"]
                self.meterData["l1_power_active"] = +1 * val["value"] / 3.0
                self.meterData["l2_power_active"] = +1 * val["value"] / 3.0
                self.meterData["l3_power_active"] = +1 * val["value"] / 3.0

    def run(self):
        while self.running == True:
            try:
                logger.info("sml serial reconnect " + self.dev)
                ser = Serial(self.dev, 9600, timeout=0.05)
                buf = b''

                while self.running == True:
                    # receive data
                    while ser.in_waiting:
                        data_in = ser.readline()
                        buf += data_in
                        time.sleep(0.1)

                    # process data
                    while True:
                        res = self.proto.parse_frame(buf)
                        end = res.pop(0)
                        buf = buf[end:]
                        if not res:
                            break
                        for msg in res[0]:
                            body = msg.get('messageBody')
                            if body:
                                logger.debug("sml serial message received")
                                self.lock.acquire()
                                self.event(body)
                                self.lock.release()
                                self.lastUpdate = datetime.datetime.now()
                            buf = b''
                        time.sleep(0.1)
            except:
                if(self.lock.locked == True):
                    self.lock.release()
                if(ser.isOpen == True):
                    ser.close()

class DbusSmartmeterService:
    def __init__(self, servicename, deviceinstance, productname='', connection='', smlreader=SmlReader()):
        self._dbusservice = VeDbusService(servicename)
        self.meter = smlreader

        logging.debug("%s /DeviceInstance = %d" %
                      (servicename, deviceinstance))

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path(
            '/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', 'SML Smart Meter service')

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', deviceinstance)
        # value used in ac_sensor_bridge.cpp of dbus-cgwacs
        self._dbusservice.add_path('/Model', 'EM24DINAV23XE1X')
        self._dbusservice.add_path('/Serial', 'MB24DINAV23XE1')
        self._dbusservice.add_path('/Role', 'grid')
        self._dbusservice.add_path('/ProductId', 45079)
        self._dbusservice.add_path('/ProductName', 'Carlo Gavazzi EM24 Ethernet Energy Meter')
        self._dbusservice.add_path('/FirmwareVersion', 65567)
        self._dbusservice.add_path('/HardwareVersion', 65566)
        self._dbusservice.add_path('/Connected', 1)
        self._dbusservice.add_path('/Position', 0) # normaly only needed for pvinverter

        #formatting
        _kwh = lambda p, v: (str(round(v, 2)) + 'KWh')
        _a = lambda p, v: (str(round(v, 1)) + 'A')
        _w = lambda p, v: (str(round(v, 1)) + 'W')
        _v = lambda p, v: (str(round(v, 1)) + 'V')

        self._dbusservice.add_path('/Ac/Energy/Forward', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/Energy/Reverse', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/L1/Current', None, gettextcallback=_a)
        self._dbusservice.add_path('/Ac/L1/Energy/Forward', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/L1/Energy/Reverse', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/L1/Power', None, gettextcallback=_w)
        self._dbusservice.add_path('/Ac/L1/Voltage', None, gettextcallback=_v)
        self._dbusservice.add_path('/Ac/L2/Current', None, gettextcallback=_a)
        self._dbusservice.add_path('/Ac/L2/Energy/Forward', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/L2/Energy/Reverse', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/L2/Power', None, gettextcallback=_w)
        self._dbusservice.add_path('/Ac/L2/Voltage', None, gettextcallback=_v)
        self._dbusservice.add_path('/Ac/L3/Current', None, gettextcallback=_a)
        self._dbusservice.add_path('/Ac/L3/Energy/Forward', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/L3/Energy/Reverse', None, gettextcallback=_kwh)
        self._dbusservice.add_path('/Ac/L3/Power', None, gettextcallback=_w)
        self._dbusservice.add_path('/Ac/L3/Voltage', None, gettextcallback=_v)
        self._dbusservice.add_path('/Ac/Power', None, gettextcallback=_w)
        self._dbusservice.add_path(path_UpdateIndex, None)
        self._dbusservice[path_UpdateIndex] = 0

        # pause 200ms before the next request
        gobject.timeout_add(200, self._update)

    def _update(self):
        try:
          # request data from SML core
          meterData = self.meter.getMeterData()

          # positive: consumption, negative: feed into grid
          self._dbusservice['/Ac/Power'] = round(meterData["power_active"], 2)
          self._dbusservice['/Ac/L1/Voltage'] = 0
          self._dbusservice['/Ac/L2/Voltage'] = 0
          self._dbusservice['/Ac/L3/Voltage'] = 0
          self._dbusservice['/Ac/L1/Current'] = 0
          self._dbusservice['/Ac/L2/Current'] = 0
          self._dbusservice['/Ac/L3/Current'] = 0
          self._dbusservice['/Ac/L1/Power'] = round(meterData["l1_power_active"], 2)
          self._dbusservice['/Ac/L2/Power'] = round(meterData["l2_power_active"], 2)
          self._dbusservice['/Ac/L3/Power'] = round(meterData["l3_power_active"], 2)
          self._dbusservice['/Ac/Energy/Forward'] = round(meterData["import_energy_active"] / 1000.0, 2)
          self._dbusservice['/Ac/Energy/Reverse'] = 0
          self._dbusservice['/Ac/L1/Energy/Forward'] = round(meterData["l1_import_energy_active"] / 1000.0, 2)
          self._dbusservice['/Ac/L2/Energy/Forward'] = round(meterData["l2_import_energy_active"] / 1000.0, 2)
          self._dbusservice['/Ac/L3/Energy/Forward'] = round(meterData["l3_import_energy_active"] / 1000.0, 2)
          self._dbusservice['/Ac/L1/Energy/Reverse'] = 0
          self._dbusservice['/Ac/L2/Energy/Reverse'] = 0
          self._dbusservice['/Ac/L3/Energy/Reverse'] = 0
        except:
            logging.info("WARNING: Could not read from meter")
            # TODO: any better idea to signal an issue?
            self._dbusservice['/Ac/Power'] = 0
            self._dbusservice['/Ac/L1/Power'] = 0
            self._dbusservice['/Ac/L2/Power'] = 0
            self._dbusservice['/Ac/L3/Power'] = 0
        # increment UpdateIndex - to show that new data is available
        index = self._dbusservice[path_UpdateIndex] + 1  # increment index
        if index > 255:   # maximum value of the index
            index = 0       # overflow from 255 to 0
        self._dbusservice[path_UpdateIndex] = index
        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change

def main():
    logging.basicConfig(level=logging.DEBUG) # use .INFO for less logging
    #thread.daemon = True # allow the program to quit

    from dbus.mainloop.glib import DBusGMainLoop

    if len(sys.argv) > 1:
        devpath = sys.argv[1]
    else:
        raise Exception("no port argument")

    # initialize SML device
    device = SmlReader()
    device.running = True
    device.dev = devpath
    device.terminateOnTimeout = 1
    device.smlTimeoutSec = 5

    # Start the thread
    device.start()

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    pvac_output = DbusSmartmeterService(
      servicename='com.victronenergy.grid.ha1',
      deviceinstance=40,
      smlreader=device
    )

    logging.info(
        'Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
    mainloop = gobject.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
