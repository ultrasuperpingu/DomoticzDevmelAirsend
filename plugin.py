"""
<plugin key="DevmelAirSend" name="Devmel AirSend" author="ping" version="0.1.0">
	<description>
		<h2>Devmel AirSend plugin</h2><br/>
		<h3>Parameters</h3>
		<ul style="list-style-type:square">
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
		<param field="Port" label="Callback Port" width="30px" required="true" default="8078"/>
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
		self._callbackAddr="http://127.0.0.1:"+Parameters["Port"]
		self._transferId=1
		self._requestCallbacks={}
		self.httpServerConns = {}
		self.httpServerConn = Domoticz.Connection(Name="Server Connection", Transport="TCP/IP", Protocol="HTTP", Port=Parameters["Port"])
		self.httpServerConn.Listen()
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
		self.bind(callbackAddr=self._callbackAddr)

	def onStop(self):
		Domoticz.Status("Stopping...")
		self.close()

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
			self.commandState(pid, addr, "UP", lambda: device.Update(nValue=1, sValue = str("100")))
		elif Command == "Stop":
			self.commandState(pid, addr, "STOP", lambda: device.Update(nValue=17, sValue = device.sValue))
			
		elif Command == "Close":
			self.commandState(pid, addr, "DOWN", lambda: device.Update(nValue=0, sValue = str("0")))
		elif Command == "On":
			self.commandState(pid, addr, "ON", lambda: device.Update(nValue=1, sValue = str("1")))
		elif Command == "Off":
			self.commandState(pid, addr, "OFF", lambda: device.Update(nValue=0, sValue = str("0")))
		elif Command == "Set Level":
			self.commandState(pid, addr, int(Level), lambda: device.Update(nValue=17, sValue = str(Level)))
		else:
			Domoticz.Error("Unknown command "+Command+" requested on device " + device.Name)

	def onDeviceAdded(self, Unit):
		device = Devices[Unit]
		Domoticz.Status(f"Device Added {device.Name}")

	def onDeviceModified(self, Unit):
		device = Devices[Unit]
		Domoticz.Status(f"Device Modified {device.Name}")

	def onDeviceRemoved(self, Unit):
		device = Devices[Unit]
		Domoticz.Status(f"Device Removed {device.Name}")

	def onConnect(self, Connection, Status, Description):
		if (Status == 0):
			Domoticz.Log(f"Connected successfully to: {Connection.Address}:{Connection.Port}")
		else:
			Domoticz.Error(f"Failed to connect ({str(Status)} to: {Connection.Address}:{Connection.Port} with error: {Description}")
		self.httpServerConns[Connection.Name] = Connection

	def onMessage(self, Connection, Data):
		#Domoticz.Log("Received: " + str(Data));
		resp = {"Status":"200 OK", "Headers": {"Accept": "Content-Type: text/html; charset=UTF-8"}, "Data": "OK"}
		Connection.Send(resp)
		if 'User-Agent' in Data['Headers'] and Data['Headers']['User-Agent'] == "AirSendWebService Callback":
			data = json.loads(Data['Data'])
			if 'events' in data:
				for e in data['events']:
					
					if 'thingnotes' in e and 'uid' in e['thingnotes']:
						uid=e['thingnotes']['uid']
						if uid in self._requestCallbacks:
							Domoticz.Log(self._requestCallbacks[uid])
							self._requestCallbacks[uid]()
							del self._requestCallbacks[uid]

	def onDisconnect(self, Connection):
		Domoticz.Log(f"onDisconnect called for connection '{Connection.Name}'.")
		if Connection.Name in self.httpServerConns:
			Domoticz.Log("deleting connection '" + Connection.Name + "'.")
			del self.httpServerConns[Connection.Name]

	def bind(self, callbackAddr=None, channel = None) -> bool:
		"""Bind a channel to listen."""
		ret = False
		if self._spurl:
			callbackStr = ''
			if callbackAddr:
				callbackStr=', "callback": "'+callbackAddr+'"'
			channel = ''
			if type(channel) is int and channel > 0:
				channel = '"channel":{"id": '+str(channel)+'},'
			payload = ('{'+channel+'"duration":0'+callbackStr+'}')
			headers = {
				"Authorization": "Bearer " + self._spurl,
				"content-type": "application/json",
				"User-Agent": "domo_airsend",
			}
			try:
				response = post(
					"http://127.0.0.1:33863/airsend/bind",
					headers=headers,
					data=payload,
					timeout=6,
				)
				if response.status_code == 200:
					ret = True
			except exceptions.RequestException:
				Domoticz.Error("Error binding listening: error code: "+response.status_code);
				pass
		return ret

	def close(self) -> bool:
		"""Close listening."""
		ret = False
		if self._spurl:
			headers = {
				"Authorization": "Bearer " + self._spurl,
				"content-type": "application/json",
				"User-Agent": "domo_airsend",
			}
			try:
				response = get(
					"http://127.0.0.1:33863/airsend/close",
					headers=headers,
					timeout=6,
				)
				if response.status_code == 200:
					ret = True
			except exceptions.RequestException:
				Domoticz.Error("Error closing listening: error code: "+response.status_code);
				pass
		return ret

	def commandState(self, pid, addr, command, callback=None):
		self.transfer(pid, addr, {"method":"PUT","type":"STATE","value":command}, self._callbackAddr, callback)

	def commandLevel(self, pid, addr, command, callback=None):
		self.transfer(pid, addr, {"method":"PUT","type":"LEVEL","value":command}, self._callbackAddr, callback)

	def transfer(self, pid, addr, note, callbackAddr=None, callback=None) -> bool:
		"""Send a command."""
		status_code = 404

		#uid = hashlib.sha256(entity_id.encode('utf-8')).hexdigest()[:12]
		jnote = json.dumps(note)
		callbackStr = ""
		if callbackAddr:
			callbackStr='"callback": "'+callbackAddr+'", '
		
		payload = (
			'{"wait": 0, '+callbackStr+'"channel":{ "id":'
			+ str(pid) +', "source\":'+str(addr)
			+ '}, "thingnotes":{"uid":"' + str(self._transferId) + '", "notes":['
			+ jnote
			+ "]}}"
		)
		if callback:
			self._requestCallbacks[self._transferId]=callback
		self._transferId+=1
		headers = {
			"Authorization": "Bearer " + self._spurl,
			"content-type": "application/json",
			"User-Agent": "domo_airsend",
		}
		try:
			response = post(
				"http://127.0.0.1:33863/airsend/transfer",
				headers=headers,
				data=payload,
				timeout=6,
			)
			ret = None
			status_code = response.status_code
		except exceptions.RequestException:
			pass
		if status_code == 200:
			return True
		Domoticz.Error("Transfer error on http://127.0.0.1:33863/airsend/transfer, "+payload+", error code="+ str(status_code))
		return False

global _plugin
_plugin = BasePlugin()

def onStart():
	global _plugin
	_plugin.onStart()

def onStop():
	global _plugin
	_plugin.onStop()

def onCommand(Unit, Command, Level, Color):
	global _plugin
	_plugin.onCommand(Unit, Command, Level, Color)

def onDeviceAdded(Unit):
	global _plugin
	_plugin.onDeviceAdded(Unit)

def onDeviceModified(Unit):
	global _plugin
	_plugin.onDeviceModified(Unit)

def onConnect(Connection, Status, Description):
	global _plugin
	_plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
	global _plugin
	_plugin.onMessage(Connection, Data)

def onDisconnect(Connection):
	global _plugin
	_plugin.onDisconnect(Connection)

def DumpConfigToLog():
	for x in Parameters:
		if Parameters[x] != "":
			Domoticz.Log( "'" + x + "':'" + str(Parameters[x]) + "'")
	return
