"""
<plugin key="DevmelAirSend" name="Devmel AirSend" author="ping" version="0.1.0">
	<description>
		<h2>Devmel AirSend plugin</h2><br/>
		<h3>Parameters</h3>
		<ul style="list-style-type:square">
			<li>Address: Webserver IP address (default: 127.0.0.1)</li>
			<li>Port: Webserver IP port (default: 33863). Probably useless since as far as I know, it can't be changed so it has to be 33863</li>
			<li>Spurl: Identification to the Airsend module in the form sp://password@ipv4. I don't know why but using ipv6 doesn't seems to work (even when using curl in command line)</li>
			<li>Devices Config: A JSON export of the device configuration.<br/>
				For example:<br/>
				<pre><code>{<br/>
    "devices":[<br/>
        {"name":"Blind1","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4098","pid":"13920","addr":"1234567"},<br/>
        {"name":"Blind2","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4098","pid":"26848","addr":"7654321"},<br/>
        {"name":"Screen Stop","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4096","opt":"18","pid":"801","addr":"01234"},<br/>
        {"name":"Screen Up","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4096","opt":"17","pid":"801","addr":"01234"},<br/>
        {"name":"Screen Down","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4096","opt":"20","pid":"801","addr":"01234"}<br/>
    ]<br/>
}</code></pre>
			</li>
		</ul>
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
		DumpConfigToLog()
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
			self.commandState(pid, addr, opt)
		elif Command == "Open":
			self.commandState(pid, addr, "UP")
		elif Command == "Stop":
			self.commandState(pid, addr, "STOP")
		elif Command == "Close":
			self.commandState(pid, addr, "DOWN")
		elif Command == "Set Level":
			self.commandState(pid, addr, int(Level))

	def onDeviceAdded(self, Unit):
		device = Devices[Unit]
		Domoticz.Log(f"onDeviceAdded {device.Name}")

	def onDeviceModified(self, Unit):
		device = Devices[Unit]
		Domoticz.Log(f"onDeviceModified {device.Name}")

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

	def commandState(self, pid, addr, command):
		self.transfer(pid, addr, {"method":"PUT","type":"STATE","value":command})
	def commandLevel(self, pid, addr, command):
		self.transfer(pid, addr, {"method":"PUT","type":"LEVEL","value":command})

	def transfer(self, pid, addr, note) -> bool:
		"""Send a command."""
		status_code = 404
		ret = False

		#uid = hashlib.sha256(entity_id.encode('utf-8')).hexdigest()[:12]
		jnote = json.dumps(note)
		
		payload = (
			'{"wait": 0, "channel":{ "id":'
			+ str(pid) +', "source\":'+str(addr)
			+ '}, "thingnotes":{"uid":"12345", "notes":['
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
		return ret

global _plugin
_plugin = BasePlugin()

def onStart():
	global _plugin
	_plugin.onStart()

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
