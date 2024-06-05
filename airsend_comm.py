import Domoticz
import json
import datetime
from requests import get, post, exceptions

_spurl=None
_currentTransferId=1
_callbackAddr=None
_requestCallbacks={}
_httpCallbackConn=None

def setSpurl(spurl):
	global _spurl
	_spurl=spurl

def getSpurl():
	global _spurl
	return _spurl

def initCallback(callbackAddr, port):
	global _callbackAddr
	global _httpCallbackConn
	_callbackAddr=callbackAddr+":"+str(port)
	_httpCallbackConn = Domoticz.Connection(Name="Callback Connection", Transport="TCP/IP", Protocol="HTTP", Port=port)
	_httpCallbackConn.Listen()

def getCallbackAddr():
	global _callbackAddr
	return _callbackAddr

def getRequestCallback(uid):
	global _requestCallbacks
	if uid in _requestCallbacks:
		return _requestCallbacks[uid][1]
	return None

def deleteRequestCallback(uid):
	global _requestCallbacks
	del _requestCallbacks[uid]

def deleteTimeoutRequests():
	global _requestCallbacks
	todelete=[]
	for uid, data in _requestCallbacks.items():
		if data[0] + datetime.timedelta(seconds=20) < datetime.datetime.now():
			Domoticz.Log("deleting request:"+str(uid))
			todelete+=[uid]
	for uid in todelete:
		Domoticz.Error("A request to a device was not executing withing 20 seconds, deleting it.")
		del _requestCallbacks[uid]

def bind(callbackAddr=None, channel = None) -> bool:
	"""Bind a channel to listen."""
	global _spurl
	ret = False
	if _spurl:
		callbackStr = ''
		if callbackAddr:
			callbackStr=', "callback": "'+callbackAddr+'"'
		channel = ''
		if type(channel) is int and channel > 0:
			channel = '"channel":{"id": '+str(channel)+'},'
		payload = ('{'+channel+'"duration":0'+callbackStr+'}')
		headers = {
			"Authorization": "Bearer " + _spurl,
			"content-type": "application/json",
			"User-Agent": "domo_airsend",
		}
		try:
			response=None
			response = post(
				"http://127.0.0.1:33863/airsend/bind",
				headers=headers,
				data=payload,
				timeout=6,
			)
			if response.status_code == 200:
				ret = True
		except exceptions.RequestException as e:
			Domoticz.Error("Exception while binding:"+str(e))
	return ret

def close() -> bool:
	"""Close listening."""
	global _spurl
	ret = False
	if _spurl:
		headers = {
			"Authorization": "Bearer " + _spurl,
			"content-type": "application/json",
			"User-Agent": "domo_airsend",
		}
		try:
			response = None
			response = get(
				"http://127.0.0.1:33863/airsend/close",
				headers=headers,
				timeout=6,
			)
			if response.status_code == 200:
				ret = True
		except exceptions.RequestException as e:
			Domoticz.Error("Exception while closing: "+str(e))
	return ret

def commandData(pid, addr, command, callback=None):
	global _callbackAddr
	transfer(pid, addr, {"method":"PUT","type":"DATA","value":command}, _callbackAddr, callback)

def commandState(pid, addr, command, callback=None):
	global _callbackAddr
	transfer(pid, addr, {"method":"PUT","type":"STATE","value":command}, _callbackAddr, callback)

def commandLevel(pid, addr, command, callback=None):
	global _callbackAddr
	transfer(pid, addr, {"method":"PUT","type":"LEVEL","value":command}, _callbackAddr, callback)

def transfer(pid, addr, note, callbackAddr=None, callback=None) -> bool:
	"""Send a command."""
	global _spurl
	global _requestCallbacks
	global _currentTransferId
	
	status_code = 404

	jnote = json.dumps(note)
	callbackStr = ""
	if callbackAddr:
		callbackStr='"callback": "'+callbackAddr+'", '

	payload = (
		'{"wait": 0, '+callbackStr+'"channel":{ "id":'
		+ str(pid) +', "source\":'+str(addr)
		+ '}, "thingnotes":{"uid":"' + str(_currentTransferId) + '", "notes":['
		+ jnote
		+ "]}}"
	)
	if callback:
		_requestCallbacks[_currentTransferId]=(datetime.datetime.now(), callback)
	_currentTransferId+=1
	headers = {
		"Authorization": "Bearer " + _spurl,
		"content-type": "application/json",
		"User-Agent": "domo_airsend",
	}
	try:
		response = None
		response = post(
			"http://127.0.0.1:33863/airsend/transfer",
			headers=headers,
			data=payload,
			timeout=6,
		)
		ret = None
		status_code = response.status_code
	except exceptions.RequestException as e:
		Domoticz.Error("Exception while transfering: "+str(e))
	if status_code == 200:
		return True
	Domoticz.Error("Transfer error on http://127.0.0.1:33863/airsend/transfer, "+payload+", error code="+ str(status_code))
	if callback:
		deleteRequestCallback(_currentTransferId-1)
	return False