# HumiSense

HumiSense ist eine Flask-basierte Anwendung zur Steuerung eines Relais basierend auf Luftfeuchtigkeit und Temperatur, die von einem SHT31-Sensor und externen APIs abgerufen werden. Die Anwendung läuft auf einem Raspberry Pi und kann über einen Hotspot mit einem Smartphone bedient werden.

## Funktionen
- Überwachung von Innen- und Aussenluftfeuchtigkeit/Temperatur.
- Automatische oder manuelle Steuerung eines Relais.
- Webinterface zur Konfiguration und Log-Anzeige.
- API für Statusabfragen und Steuerung.

## Voraussetzungen
- Raspberry Pi (getestet mit Raspberry Pi OS).
- SHT31-Sensor (I2C-verbunden).
- Relais und LED (GPIO-verbunden).
- Python 3.7+.
- Internetzugang (für API-Daten).

## Installation

```bash
### 1. Repository klonen

git clone https://github.com/arnventures/HumiSense/
cd HumiSense

### 2. Virtuelle Umgebung erstellen und aktivieren

bash

python3 -m venv venv
source venv/bin/activate

### 3. Abhängigkeiten installieren
bash

pip install -r requirements.txt

Erstelle eine requirements.txt mit:

flask
flask-cors
requests
smbus2
lgpio
python-dateutil
file-read-backwards

### 4. Hardware vorbereiten
Verbinde den SHT31-Sensor an I2C (Standardadresse: 0x44).

Verbinde das Relais an GPIO 17 und die LED an GPIO 5.

### 5. Anwendung starten (Entwicklung)
bash

python3 app.py

Öffne einen Browser und gehe zu http://localhost:3000 oder http://<raspberry-pi-ip>:3000.

