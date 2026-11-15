TODO:
	- wire in the new sensor
		- update the grafana dashboard
		- update thresholds for nox and voc
	- further tweak display reporter
		- maybe slightly smaller text
		- maybe integer for voc and nox
		- maybe tweak the gridlayout
	- better error handling
	- get the notification reporter working
	- see TODOS in code files
	- update to keep secrets in settings.toml
	- use asyncio (or something) to make it respond to button presses by changing the display mode - do this now but it is janky
  - in an effort to make it resilient, i transiently write some errors to the screen
    - and others i only ever print to the serial console... it would be nice to log errors somehow and print something persistently to the screen to indicate that i should check those logs
    - https://learn.adafruit.com/circuitpython-essentials/circuitpython-storage
	- ask gemini for other ways to improve the code (and make it more pythonic)
	- update this file...
		- as built
	- push all changes upstream

## Development workflow

Edit application code in this repository and connect the board over USB so it
mounts as `/Volumes/CIRCUITPY` (not `FTHRS3BOOT`). Install Circup on your Mac with
`pipx install circup` and make sure `circup` is available in the VS Code terminal.
The dependency tasks add pipx's default executable directory (`~/.local/bin`) to
their PATH, so they also work when VS Code was launched without that directory
in its environment. For interactive terminals, run `pipx ensurepath` and restart
the terminal if `circup` is not found.

Use **Terminal > Run Task** to run the tasks in [.vscode/tasks.json](.vscode/tasks.json):

- **add_deps**: Scan local `code.py` and all Python files directly in `reporters/`,
  install their recognized bundle libraries and dependencies on the board, then
  save the board's library inventory to local `requirements.txt`. This includes
  optional reporters, but excludes development snippets. Review and commit the
  generated dependency list. It inventories all installed libraries, including
  any unrelated ones; it does not remove unused libraries.
- **install_deps**: Install libraries from the committed `requirements.txt` onto
  the board. Use this when setting up a fresh board.
- **deploy**: Copy local `settings.toml`, Python files in `reporters/`, then
  `code.py`, and flush pending writes. Local settings overwrite the board's
  settings on every deployment; deployment fails before copying if the local
  file is missing. This does not copy `lib/`, snippets, Git/editor files, or
  `secrets.py`, and does not delete existing board files. CircuitPython may
  reload while files are copied; check the serial console after deployment.

For initial setup, run `add_deps`, configure local `settings.toml`, then `deploy`.
Keep `settings.toml` excluded from Git even though it is deployed. Restore
`secrets.py` separately if the application still uses it; it is excluded from Git
and deployment. Back up private configuration separately before firmware or
bootloader upgrades.

For library updates, run `circup --path /Volumes/CIRCUITPY update --all`, test the
application, then run `circup --path /Volumes/CIRCUITPY freeze -r` and review the
updated dependency list. Circup selects compiled libraries for the board's
CircuitPython version; the repository's existing `lib/` is not deployed.

## Network reporting

The database and notification reporters skip requests and log to the serial
console when Wi-Fi is disconnected or no IPv4 address is available. Sensor
sampling and display reporting can continue while CircuitPython reconnects.
Requests use a 10-second socket timeout and log failures; skipped readings are
not queued. Notification cooldown starts only after Pushover confirms acceptance.
The reporters do not run their own reconnect loops.

Run the host-side reporter tests without board hardware using
`python3 -m unittest discover -s tests`.

https://circuitpython.org/board/adafruit_feather_esp32s3_reverse_tft/

https://learn.adafruit.com/adafruit-ens160-mox-gas-sensor/circuitpython-python
https://learn.adafruit.com/adafruit-scd30/python-circuitpython
https://learn.adafruit.com/pmsa003i/python-circuitpython

https://www.airthings.com/view-plus

- Particulates (PM1, PM2.5, & PM10)
- VOCs
- CO2
- Temp, humidity, pressure
- Radon

===
As built:
- scd30 measures CO2 and temp
- ens160 measures VOCs
- pm25 measures pm2.5, pm10, pm100
- read the sensors every two minutes
	- also calibrate the temp and humidity of the ens160 based on the readings from the scd30
- write the data to the screen
- write the data to the influxdb database running on pi-anemoi
- change display mode by pressing button 0
- press button 1 or 2 while powering it on causes it to calibrate the scd30
	- button 1 calibrates against eCO2 reading from the ens160 this is probably not very accurate
	- button 2 calibrates against outside air and assumes it is 425 which should be in the right ballpark

TODO:
- reconnect to wifi if we lose connection
	- also do this for the basement monitor
- skip reading the sensors if the data is invalid
	- i already try to do this but it needs improvement
- the way i have coded it to respond but button 0 is janky
- it would be nice to measure radon
- it would be nice to measure CO
- i need an enclosure
===

Original plan:
1. read sensors every 5 minutes. I could do it more frequently but the airthings has an interval of 5 minutes and i think we should not update the e-ink display (if that is what i end up using) any more frequently than every 3 minutes.
2. send data to reporters
	1. post data to influxdb
	2. write data to display (if using a color display, i could use color to denote that it is in or out of expected range - check airthings specs for ranges to use
	3. if out of range post data to pushover

===

I'd like to do something like this to change the display mode (what info it dispays) when you press the 3 buttons
https://learn.adafruit.com/adafruit-esp32-s3-tft-feather/multitasking-with-asyncio
pm25, aqi, co2, hum, temp, voc (there are other pm details i could show too)
pm25, aqi, co2, voc

________________________
| 2.5               200 |
| PM2.5             VOC |
|                       |
| 22                686 |
| AQI               CO2 |
------------------------


===

## threshold levels
Particulate matter (PM2.5)
red ≥25 μg/m3
yellow ≥10 and <25 μg/m3
green <10 μg/m3

Carbon dioxide (CO2)
red ≥1000 ppm
yellow ≥800 and <1000 ppm
green <800 ppm

Humidity
red ≥70 %
yellow ≥60 and <70 %
green ≥30 and <60 %
yellow ≥25 and <30 %
red <25 %

Temperature (°F)
red >77 °F
yellow ≥64 and ≤77 °F
blue <64 °F

Airborne chemicals (VOC)
red ≥2000 ppb
yellow ≥250 and <2000 ppb
green <250 ppb

---

Radon (pCi/L)
red ≥4 pCi/L
yellow ≥2.7 and <4 pCi/L
green <2.7 pCi/L

Radon (Bq/m3)
red ≥150 Bq/m3
yellow ≥100 and <150 Bq/m3
green <100 Bq/m3