# DomoticzDevmelAirsend
Devmel Airsend Plugin for Domoticz
## Parameters
 * Callback Port: Plugin Http Server port where the Webserver will send the callbacks (default: 8078).
 * Spurl: Identification to the Airsend module in the form sp://password@ipv4. I don't know why but using ipv6 doesn't seems to work (even when using curl in command line)
 * Devices Config: A JSON export of the device configuration (localip field is ignored).
				For example:
```json
{
    "devices":[
        {"name":"Blind1","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4098","pid":"13920","addr":"1234567"},
        {"name":"Blind2","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4098","pid":"26848","addr":"7654321"},
        {"name":"Screen Stop","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4096","opt":"18","pid":"801","addr":"01234"},
        {"name":"Screen Up","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4096","opt":"17","pid":"801","addr":"01234"},
        {"name":"Screen Down","localip":"xxxx::xxxx:xxxx:xxxx:xxxx","type":"4096","opt":"20","pid":"801","addr":"01234"}
    ]
}
```
