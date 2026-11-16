TODO:
	- i wonder if i could fit 4 metrics on the first screen: pm2.5, co2, voc, nox
  - update libs: circup --path /Volumes/CIRCUITPY update --all
	- suggestions from claude:
		- The Wi-Fi failure reason gets lost.
		- If the first read fails, the screen sticks on “Measurement started”.
	- reconnect if we lose wifi - from a conversation with claude:
		- Fall back to a hard reset. If reconnecting fails N times in a row, microcontroller.reset() is a blunt but effective fix, and it’s what most always-on CircuitPython projects do. You can also enable the watchdog (microcontroller.watchdog) so a hang forces a reboot on its own.
		- Optional: buffer readings. If you care about not losing data during outages, keep the last few readings in a list and flush them when Wi-Fi returns. With a 30s to 5 min interval you’d only need a small buffer, and RAM is the limit, so cap it.
	- get the notification reporter working
	- see TODOS in code files
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
  `code.py`, `thresholds.py`, and flush pending writes. Local settings overwrite the board's
  settings on every deployment; deployment fails before copying if the local
  file is missing. This does not copy `lib/`, snippets, or Git/editor files, and does not delete existing board files. CircuitPython may
  reload while files are copied; check the serial console after deployment.

For initial setup, run `add_deps`, configure local `settings.toml`, then `deploy`.
Back up private configuration separately before firmware or bootloader upgrades.

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

https://circuitpython.org/board/adafruit_feather_esp32s3_reverse_tft/

Inspired by https://www.airthings.com/view-plus

- Particulates (PM1, PM2.5, & PM10)
- VOCs
- CO2
- Temp, humidity, pressure
- Radon