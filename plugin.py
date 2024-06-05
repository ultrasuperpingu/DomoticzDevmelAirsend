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
			<li>Remote Mapping Config: A JSON which bind blind remotes to Domoticz blinds.<br/>
				For example:<br/>
				<pre><code>{<br/>
    "remotes":[<br/>
        {"remoteAddr":1111111, "pid":13920, "blindAddr":1234567},<br/>
        {"remoteAddr":2222222, "pid":26848, "blindAddr":7654321}<br/>
    ]<br/>
}</code></pre>
			</li>
		</ul>
	</description>
	<params>
		<param field="Port" label="Callback Port" width="30px" required="true" default="8078"/>
		<param field="Mode1" label="Spurl" width="400px" required="true" default="sp://xxxxxxxxxxxxxxxx@xxx.xxx.xxx.xxx"/>
		<param field="Mode2" label="Devices Config" width="400px" rows="10" default=""/>
		<param field="Mode3" label="Remote Mapping Config" width="400px" rows="10" default=""/>
	</params>
</plugin>
"""
#sudo pip3 install requests

import Domoticz
import json
import airsend_comm


DisableUserAgentCheck=False
_remotesMapping={}
PushButtonCfg=(244,79,9)
SwitchCfg=(244,79,0)
BlindCfg=(244,58,3)
BlindPositionCfg=(244,58,21)
TempCfg=(80,5,0)
TempHumCfg=(82,1,0)
IllumCfg=(246,1,0)
currentUnit=1
def CreateDeviceIfNeeded(Name, DeviceID, DeviceFullType):
	dev=None
	global currentUnit
	devUnit=[Unit for Unit,Dev in Devices.items() if Dev.DeviceID == DeviceID]
	if len(devUnit)==0:
		while currentUnit in Devices:
			currentUnit+=1
			if currentUnit < 1 or currentUnit > 255:
				return None
		dev = Domoticz.Device(Name=Name, Unit=currentUnit, DeviceID=DeviceID, Type=DeviceFullType[0], Subtype=DeviceFullType[1], Switchtype=DeviceFullType[2], Used=True)
		Domoticz.Status(f"Creating device {Name} with DeviceID={DeviceID} and type={DeviceFullType[2]}")
		dev.Create()
	else:
		dev=Devices[devUnit[0]]
	return dev

def getPathValue (dict, path, separator = '/', default=None):
	pathElements = path.split(separator)
	element = dict
	for pathElement in pathElements:
		if pathElement not in element:
			return default
		element = element[pathElement]
	return element


def onStart():
	global _remotesMapping
	Domoticz.Status("Starting...")
	airsend_comm.setSpurl(Parameters["Mode1"])
	airsend_comm.initCallback("http://127.0.0.1",Parameters["Port"])
	if Parameters["Mode3"] and len(Parameters["Mode3"])>0:
		_remotesMapping=getPathValue(json.loads(Parameters["Mode3"]),'remotes')
	Domoticz.Status("Creating callback connector...")
	devicesSpecs=json.loads(Parameters["Mode2"])
	for dev in getPathValue(devicesSpecs,"devices"):
		name=getPathValue(dev,"name")
		pid=getPathValue(dev,"pid")
		addr=getPathValue(dev,"addr")
		opt=getPathValue(dev,"opt")
		typ=getPathValue(dev,"type")
		TypeCfg=PushButtonCfg
		if typ=="4097":
			TypeCfg=SwitchCfg
		elif typ=="4098":
			TypeCfg=BlindCfg
		elif typ=="4099":
			TypeCfg=BlindPositionCfg
		CreateDeviceIfNeeded(name, str(pid)+"_"+str(addr)+"_"+str(opt), TypeCfg)
	Domoticz.Status("Asking for callback to the WebService...")
	airsend_comm.bind(callbackAddr=airsend_comm.getCallbackAddr())
	Domoticz.Status("Started...")

def onStop():
	Domoticz.Status("Stopping...")
	airsend_comm.close()

def onCommand(Unit, Command, Level, sColor):
	device = Devices[Unit]
	Domoticz.Log(f"{device.Name}, {device.DeviceID}: Command: '{Command}', Level: {Level}, Color: {sColor}")
	fields=device.DeviceID.split('_')
	pid=int(fields[0])
	addr=int(fields[1])
	opt=None
	if fields[2] != "None" and len(fields[2])>0:
		opt=int(fields[2])
	
	if opt:
		airsend_comm.commandData(pid, addr, opt)
	elif Command == "Open":
		airsend_comm.commandState(pid, addr, "UP", lambda: device.Update(nValue=1, sValue = str("100")))
	elif Command == "Stop":
		airsend_comm.commandState(pid, addr, "STOP", lambda: device.Update(nValue=17, sValue = device.sValue))
		
	elif Command == "Close":
		airsend_comm.commandState(pid, addr, "DOWN", lambda: device.Update(nValue=0, sValue = str("0")))
	elif Command == "On":
		airsend_comm.commandState(pid, addr, "ON", lambda: device.Update(nValue=1, sValue = str("1")))
	elif Command == "Off":
		airsend_comm.commandState(pid, addr, "OFF", lambda: device.Update(nValue=0, sValue = str("0")))
	elif Command == "Set Level":
		airsend_comm.commandState(pid, addr, int(Level), lambda: device.Update(nValue=17, sValue = str(Level)))
	else:
		Domoticz.Error("Unknown command "+Command+" requested on device " + device.Name)

def onDeviceAdded(Unit):
	device = Devices[Unit]
	Domoticz.Status(f"Device Added {device.Name}")

def onDeviceModified(Unit):
	device = Devices[Unit]
	Domoticz.Status(f"Device Modified {device.Name}")

def onDeviceRemoved(Unit):
	device = Devices[Unit]
	Domoticz.Status(f"Device Removed {device.Name}")

def onConnect(Connection, Status, Description):
	if (Status == 0):
		Domoticz.Log(f"Connected successfully to: {Connection.Address}:{Connection.Port}")
	else:
		Domoticz.Error(f"Failed to connect ({str(Status)} to: {Connection.Address}:{Connection.Port} with error: {Description}")

def onMessage(Connection, Data):
	global _remotesMapping
	Domoticz.Log("Received: " + str(Data));
	resp = {"Status":"200 OK", "Headers": {"Accept": "Content-Type: text/plain; charset=UTF-8"}, "Data": "OK"}
	Connection.Send(resp)
	if DisableUserAgentCheck or ('User-Agent' in Data['Headers'] and Data['Headers']['User-Agent'] == "AirSendWebService Callback"):
		data = json.loads(Data['Data'])
		if 'events' in data:
			for e in data['events']:
				channel = None
				if "channel" in e:
					channel = e['channel']
					Domoticz.Log(str(channel))
				if 'thingnotes' in e:
					tn=e['thingnotes']
					if 'uid' in tn: # is it a command callback
						uid=e['thingnotes']['uid']
						cb=airsend_comm.getRequestCallback(uid)
						if cb:
							Domoticz.Log(cb)
							cb()
							airsend_comm.deleteRequestCallback(uid)
							return
					#checking if it's sensors or remote bindings
					temp=None
					hum=None
					ill=None
					receivedCommand=None
					for note in tn['notes']:
						if note['method'] == 2: #Infos
							if note['type'] == 2: #Temperature
								temp=round(note['value']-273.10,1) #should be 273.15 but it does not match what the sensor is sending
							elif note['type'] == 3: #Illumination
								ill=float(note['value'])
							elif note['type'] == 4: #Humidity
								hum=float(note['value'])
						elif note['method'] == 1: #Put
							if note['type'] == 0: #State
								if note['value'] == 35: #Up
									receivedCommand=(1,"100")
								elif note['value'] == 34: #Down
									receivedCommand=(0,"0")
								elif note['value'] == 17: #Stop
									receivedCommand=(17,"50")
								elif note['value'] == 21: #Close
									receivedCommand=(0,"0")
								elif note['value'] == 22: #Open
									receivedCommand=(1,"100")
								elif note['value'] == 19: #Off
									receivedCommand=(0,"0")
								elif note['value'] == 20: #On
									receivedCommand=(1,"1")
					if temp != None and hum != None:
						dev=CreateDeviceIfNeeded("Temp+Hum",str(channel['id'])+"_"+str(channel['source'])+"_None", TempHumCfg)
						dev.Update(nValue=0, sValue=str(temp)+";"+str(hum))
					else:
						if temp != None:
							dev=CreateDeviceIfNeeded("Temp",str(channel['id'])+"_"+str(channel['source'])+"_None", TempCfg)
							dev.Update(nValue=0, sValue=str(temp))
						if hum != None:
							dev=CreateDeviceIfNeeded("Humidity",str(channel['id'])+"_"+str(channel['source'])+"_None", HumCfg)
							dev.Update(nValue=0, sValue=str(hum))
					if ill != None:
						dev=CreateDeviceIfNeeded("Lux",str(channel['id'])+"_"+str(channel['source'])+"_None", IllumCfg)
						dev.Update(nValue=ill, sValue=str(ill))
					#Checking if it's remote binding
					remoteMap=[remote for remote in _remotesMapping if remote['pid'] == channel['id'] and remote['remoteAddr'] == channel['source']]
					if receivedCommand != None and len(remoteMap) > 0:
						remote=remoteMap[0]
						Domoticz.Log("Received a blind remote signal: "+str(remote))
						DeviceID=str(remote['pid'])+"_"+str(remote['blindAddr'])
						Domoticz.Log(DeviceID)
						devUnit=[Unit for Unit,Dev in Devices.items() if Dev.DeviceID.startswith(DeviceID)]
						if len(devUnit) > 0:
							Domoticz.Log("Updating device "+Devices[devUnit[0]].Name+" with status : "+receivedCommand[1])
							Devices[devUnit[0]].Update(nValue=receivedCommand[0],sValue=receivedCommand[1])

def onDisconnect(Connection):
	Domoticz.Log(f"onDisconnect called for connection '{Connection.Name}'.")

def onHeartbeat():
	airsend_comm.deleteTimeoutRequests()

