"""
<plugin key="DevmelAirSend" name="Devmel AirSend" author="ping" version="0.1.0">
	<description>
Devmel AirSend plugin.<br/><br/>
	</description>
	<params>
		<param field="Address" label="WebServer Address" width="300px" required="true" default="127.0.0.1"/>
		<param field="Port" label="WebServer Port" width="300px" required="true" default="33863"/>
		<param field="Mode1" label="Spurl" width="400px" required="true" default="sp://xxxxxxxxxxxxxxxx@xxx.xxx.xxx.xxx"/>
		<param field="Mode2" label="Devices Config" width="400px" rows="10" default=""/>
	</params>
</plugin>
"""
#sudo pip3 install requests

import Domoticz
from datetime import datetime
from requests import get, post, exceptions
import json

PushButtonCfg=(244,79,9)
SwitchCfg=(244,79,0)
BlindCfg=(244,58,3)
BlindPositionCfg=(244,58,21)
currentUnit=1
def CreateDeviceIfNeeded(Name, DeviceID, DeviceFullType):
	dev=None
	global currentUnit
	devUnit=[Unit for Unit,Dev in Devices.items() if Dev.DeviceID == DeviceID]
	if len(devUnit)==0:
		while currentUnit in Devices:
			currentUnit+=1
			if currentUnit < 0 or currentUnit > 255:
				return None
		dev = Domoticz.Device(Name=Name, Unit=currentUnit, DeviceID=DeviceID, Type=DeviceFullType[0], Subtype=DeviceFullType[1], Switchtype=DeviceFullType[2], Used=True)
		dev.Create()
	else:
		dev=Devices[devUnit[0]]
	return dev

class BasePlugin:
	# Return a path in a dictionary or default value if not existing
	def getPathValue (self, dict, path, separator = '/', default=None):
		pathElements = path.split(separator)
		element = dict
		for pathElement in pathElements:
			if pathElement not in element:
				return default
			element = element[pathElement]
		return element


	def onStart(self):
		#if Parameters["Mode6"] != "0":
		#	DumpConfigToLog()
		#	Domoticz.Debugging(int(Parameters["Mode6"]))
		#Domoticz.Heartbeat(int(Parameters["Mode1"]))
		self._spurl=Parameters["Mode1"]
		self._serviceurl=Parameters["Address"]+":"+Parameters["Port"]
		devicesSpecs=json.loads(Parameters["Mode2"])
		for dev in self.getPathValue(devicesSpecs,"devices"):
			name=self.getPathValue(dev,"name")
			pid=self.getPathValue(dev,"pid")
			addr=self.getPathValue(dev,"addr")
			opt=self.getPathValue(dev,"opt")
			typ=self.getPathValue(dev,"type")
			Domoticz.Log(name+" "+pid+" "+typ)
			TypeCfg=PushButtonCfg
			if typ=="4097":
				TypeCfg=SwitchCfg
			elif typ=="4098":
				TypeCfg=BlindCfg
			elif typ=="4099":
				TypeCfg=BlindPositionCfg
			CreateDeviceIfNeeded(name, pid+"_"+addr+"_"+str(opt), TypeCfg)

	def onConnect(self, Connection, Status, Description):
		pass

	def onMessage(self, Connection, Data):
		Domoticz.Debug("onMessage called for connection: '"+Connection.Name+"'")

	def onHeartbeat(self):
		Domoticz.Debug("Heartbeating...")
		
	# Called when a command is sent to one device linked to this plug-in
	def onCommand(self, Unit, Command, Level, sColor):
		device = Devices[Unit]
		Domoticz.Log(f"{device.Name}, {device.DeviceID}: Command: '{Command}', Level: {Level}, Color: {sColor}")
		fields=device.DeviceID.split('_')
		pid=int(fields[0])
		addr=int(fields[1])
		opt=None
		if fields[2] != "None" and len(fields[2])>0:
			opt=int(fields[2])
		
		if opt:
			self.command(pid, addr, opt)
		elif Command == "Open":
			self.command(pid, addr, "UP")
		elif Command == "Stop":
			self.command(pid, addr, "STOP")
		elif Command == "Close":
			self.command(pid, addr, "DOWN")

	# Called when a device is added to this plug-in
	def onDeviceAdded(self, Unit):
		device = Devices[Unit]
		Domoticz.Log(f"onDeviceAdded {device.Name}")

	# Called when a device managed by this plug-in is (externally) modified
	# This is the case when callback is called by AirSend web service
	# One message will be received for each event (they're split by callback)
	def onDeviceModified(self, Unit):
		device = Devices[Unit]
		Domoticz.Log(f"onDeviceModified {device.Name}")

	# Called when a device is removed from this plug-in
	def onDeviceRemoved(self, Unit):
		device = Devices[Unit]
		Domoticz.Log(f"onDeviceRemoved {device.Name}")

	def bind(self, bind = None) -> bool:
		"""Bind a channel to listen."""
		ret = False
		if self._serviceurl and self._spurl and type(bind) is int and bind > 0:
			payload = ('{"channel":{"id": '+str(bind)+'},\"duration\":0,\"callback\":\"http://127.0.0.1/\"}')
			headers = {
				"Authorization": "Bearer " + self._spurl,
				"content-type": "application/json",
				"User-Agent": "domo_airsend",
			}
			try:
				response = post(
					self._serviceurl + "airsend/bind",
					headers=headers,
					data=payload,
					timeout=6,
				)
				if response.status_code == 200:
					ret = True
			except exceptions.RequestException:
				pass
		return ret

	def command(self, pid, addr, command):
		self.transfert(pid, addr, {"method":"PUT","type":"STATE","value":command})

	def transfert(self, pid, addr, note, entity_id = 12345) -> bool:
		"""Send a command."""
		status_code = 404
		ret = False
		
		if self._serviceurl and self._spurl and entity_id is not None:
			#uid = hashlib.sha256(entity_id.encode('utf-8')).hexdigest()[:12]
			uid="12345"
			jnote = json.dumps(note)
			
			payload = (
				'{"wait": 0, "channel":{ "id":'
				+ str(pid) +', "source\":'+str(addr)
				+ '}, "thingnotes":{"uid":"0x'+uid+'", "notes":['
				+ jnote
				+ "]}}"
			)
			headers = {
				"Authorization": "Bearer " + self._spurl,
				"content-type": "application/json",
				"User-Agent": "domo_airsend",
			}
			try:
				response = post("http://"+
					self._serviceurl + "/airsend/transfer",
					headers=headers,
					data=payload,
					timeout=6,
				)
				ret = None
				status_code = response.status_code
			except exceptions.RequestException:
				pass
		if status_code == 200:
			return ret
		Domoticz.Error("Transfer error "+"http://"+self._serviceurl + "/airsend/transfer: error code="+ str(status_code)+", "+payload)


global _plugin
_plugin = BasePlugin()

def onStart():
	global _plugin
	_plugin.onStart()

def onConnect(Connection, Status, Description):
	global _plugin
	_plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
	global _plugin
	_plugin.onMessage(Connection, Data)

def onHeartbeat():
	global _plugin
	_plugin.onHeartbeat()

def onCommand(Unit, Command, Level, Color):
	global _plugin
	_plugin.onCommand(Unit, Command, Level, Color)

def onDeviceAdded(Unit):
	global _plugin
	_plugin.onDeviceAdded(Unit)

def onDeviceModified(Unit):
	global _plugin
	_plugin.onDeviceModified(Unit)

def DumpConfigToLog():
	for x in Parameters:
		if Parameters[x] != "":
			Domoticz.Log( "'" + x + "':'" + str(Parameters[x]) + "'")
	return

