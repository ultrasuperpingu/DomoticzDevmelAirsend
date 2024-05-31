# DomoticzDevmelAirsend
Plugin Devmel Airsend pour Domoticz

## Prerequisites
### Python 3
Votre version de Domoticz doit avoir été compilé avec le support python et python3 doit être installé.

### Airsend Webserver
Airsend Webserver doit être installé et démarré sur la même machine que Domoticz.
Airsend Webserver: http://devmel.com/dl/AirSendWebService.tgz

Vous pouvez faire du Airsend Webserver un service.
Voici un exemple de fichier service:

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
Modifier en fonction de vos besoins (adaptez la version lancée en fonction de votre architecture, adaptez l'utilisateur et le group, etc), copier ce fichier dans /etc/systemd/system. Vous pouvez ensuite installer le service avec la commande:
```bash
systemctl enable airsend
```
Penser ensuite a le démarrer (ou a rebooter la machine)

Pour utiliser le webserver via un container, vous trouverez de la documentation pou utiliser Docker su les forums Home Assitant par exemple.

### Dépendances Python
Le plugin utilise le package python requests. Pour l'installer:
```bash
sudo pip3 install requests
```

## Paramètres
 * Callback Port: Port à utiliser pour les callbacks (défaut: 8078).
 * Spurl: Identification to the Airsend module in the form sp://password@ipv4. I don't know why but using ipv6 doesn't seems to work (even when using curl in command line)
 * Devices Config: Un export JSON des périphériques (le champs localip est ignoré).
				Par exemple:
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
