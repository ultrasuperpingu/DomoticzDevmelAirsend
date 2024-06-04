Other Languages: [Français](README.fr.md)

# DomoticzDevmelAirsend
Devmel Airsend Plugin for Domoticz

## Prerequisites
### Python 3
Your Domoticz has to be compiled with python support and python3 have to be installed.

### Airsend Webserver
The Airsend Webserver has to be installed and running on the same machine than Domoticz.
The Airsend Webserver can be found here: http://devmel.com/dl/AirSendWebService.tgz

You can make an airsend service.
Here is an example of a service file:

```ini
[Unit]
       Description=airsend_service
       After=network-online.target
       Wants=network-online.target
[Service]
       User=domoticz
       Group=domoticz
       ExecStart=/home/domoticz/AirSendWebService/bin/unix/arm/AirSendWebService
       WorkingDirectory=/home/domoticz
       Restart=on-failure
       RestartSec=1m
       #StandardOutput=null
[Install]
       WantedBy=multi-user.target
```
Modify it with your needs (adapt the folder to run the correct architecture, adapt the user and group, etc), copy it to /etc/systemd/system. You can then install it to make it run on startup with:
```bash
systemctl enable airsend
```

You can also run it as a container. To do this, you can find some documentation to use it with docker on home assistant related forums for example.

### Python module dependancies
The plugin needs the requests package to be able to send http requests to the webserver. You can install it with the command:
```bash
sudo pip3 install requests
```

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
 * Remote Mapping Config: A JSON which bind blind remotes to Domoticz blinds.
				For example:
```json
{
    "remotes":[
        {"remoteAddr":1111111, "pid":13920, "blindAddr":1234567},
        {"remoteAddr":2222222, "pid":26848, "blindAddr":7654321}
    ]
}