## Summary

Indoor air quality monitor: an Adafruit ESP32-S3 Reverse TFT Feather running
CircuitPython, with a Sensirion SEN66 sensor (Adafruit SEN6x breakout, over
STEMMA QT). Readings go to the built-in screen and to InfluxDB.

Board: https://circuitpython.org/board/adafruit_feather_esp32s3_reverse_tft/

Inspired by https://www.airthings.com/view-plus

- Particulates (PM1, PM2.5, & PM10)
- VOCs
- CO2
- Temp, humidity, pressure
- Radon

### What it does

- Reads the SEN66 every 30 seconds (`sampling_interval` in `settings.toml`). One sensor provides everything: CO2 (ppm), temperature (shown in °F), humidity (%RH), VOC index, NOx index, and
  PM1 / PM2.5 / PM4 / PM10 (µg/m³).
- Hands each reading to every reporter. A failing reporter never stops the others
  or the sensor loop.
  - **Display** (`reporters/display.py`): shows the readings on the TFT, colored
    green / yellow / red against the ranges in `thresholds.py`.
  - **InfluxDB** (`reporters/db.py`): writes the readings to InfluxDB 1.x (running
    on pi-anemoi) over HTTP using line protocol.
  - **Notifications** (`reporters/notifier.py`, Pushover): disabled; it still
    needs updating.
- Display pages, cycled with button 0 (D0):
  1. PM2.5, VOC, CO2, NOx (2x2)
  2. Temp, humidity
  3. PM1, PM2.5, PM4, PM10 (2x2)
  4. Error log
- Error reporting: while any source is failing, a red `!` shows in the top-right
  corner of every page and the NeoPixel stays red between samples (it flashes
  green while sampling and is off when all is well). The error log page lists
  each source that has failed (sensor, display, influx, watchdog) with how long
  it has been failing and the latest message. Recovered sources stay listed as
  "ok for ..." so a blip you missed is still visible.

### Reliability

- **Watchdog:** resets the board if the main loop stalls. The timeout is 3x the
  sampling interval (60 second minimum), and it is fed only after a successful
  sensor read, so a dead or hung sensor reboots the board but a Wi-Fi or InfluxDB
  outage does not. After a watchdog reset the error log shows "watchdog:
  restarted after stall" until the first good read.
- **Wi-Fi / InfluxDB:** the reporter reconnects Wi-Fi when it drops and rebuilds
  its HTTP session. Requests time out after 5 seconds and failures show up in the
  error log. Readings that fail to send are not queued.
- **Sensor:** the SEN66's sticky error flags are cleared at boot and after any
  failed read, so a stale flag can't keep the sensor failing. If the sensor can't
  be reached at boot, the error is shown on the log page and setup is retried every
  5 seconds instead of crashing; the watchdog reboots the board if that goes on
  past its timeout.
- **Memory:** `gc.collect()` runs once per sampling cycle, so collection happens
  on our schedule and heap fragmentation stays low.

### Sensor setup notes

- Altitude is set to 1525 m at boot for CO2 pressure compensation.
- Boot waits about 15 seconds for the sensor to warm up (CO2 and NOx are unknown
  for the first several seconds). The VOC and NOx indexes take hours to settle
  after a power-on, so ignore them at first.
- Fan cleaning is not used. Unlike the SEN5x, the SEN6x has no automatic cleaning
  (Sensirion removed it as unnecessary), and the manual command isn't called.

### Configuration and files

- `settings.toml` (gitignored): Wi-Fi (`CIRCUITPY_WIFI_SSID`,
  `CIRCUITPY_WIFI_PASSWORD`), altitude (`altitude`), sampling interval (`sampling_interval`), InfluxDB (`db_host`, `db_port`, `db_database`,
  `db_table`, `db_username`, `db_password`), and Pushover (`pushover_user`,
  `pushover_token`) for the notifier.
- `thresholds.py`: caution and danger ranges for each metric, as half-open
  `(min, max)` pairs. Safe to commit.
- `code.py`: setup and the main loop.
- `reporters/`: `display.py`, `db.py`, `notifier.py`, `flaky.py` (a test reporter
  that fails a few times in a row, to exercise the error handling), and `log.py`
  (currently empty).
- `tests/` and `snippets/`: host-side tests and scratch code that isn't deployed.

TODO:
	- get the notification reporter working
	- what about a reporter_manager class?
	- ask claude for other suggestions
	- update this file - as built

## Development workflow

NOTE: This board is setup for circuitpython web workflow just for convenience. Thus the usb mass storage is disabled by default. When using the below workflow, you must hold D1 while it boots to enable usb mass storage.

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

A network problem never stops sensor sampling or the display. Each reporter runs
inside a `try` in `code.py`; if it raises, the error is recorded in the display's
error log under that reporter's name and clears itself after the next success.

**InfluxDB reporter** (`reporters/db.py`)

- Before each write it checks Wi-Fi and reconnects with the credentials in
  `settings.toml` if the connection dropped. It builds a new HTTP session after a
  reconnect and after any failed request, since a session tied to a dropped
  connection can't be trusted.
- Writes use a 5-second timeout. Wi-Fi being unavailable, a request exception, or
  a non-2xx response all raise, so they show up in the error log as "influx" and
  turn on the `!` indicator.
- Fields that are `None` or NaN are left out of the line, because one bad value
  makes InfluxDB reject the whole write. If nothing is left, nothing is sent.
- Readings that fail to send are not queued, so an outage leaves a gap in the
  data.

**Notification reporter** (`reporters/notifier.py`) is disabled and still reflects
an earlier version of the project: it expects a `delta` reading the SEN66 doesn't
produce, takes no part in the error log, and catches its own errors. It skips and
logs to the serial console when Wi-Fi is down, uses a 10-second timeout, and starts
its once-a-day cooldown only after Pushover confirms acceptance. It needs updating
before it is turned on.

Run the host-side tests without board hardware using
`python3 -m unittest discover -s tests`. `tests/test_network_reporters.py` still
targets the earlier reporters (it constructs `InfluxDbReporter` with a settings
dict and expects skip-and-log behavior and a 10-second timeout), so it needs
updating to match the current ones.