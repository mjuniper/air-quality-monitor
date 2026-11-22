## Summary

Indoor air quality monitor: an Adafruit ESP32-S3 Reverse TFT Feather running
CircuitPython, with a Sensirion SEN66 sensor (Adafruit SEN6x breakout, over
STEMMA QT). Readings go to the built-in screen and to InfluxDB.

Board: https://circuitpython.org/board/adafruit_feather_esp32s3_reverse_tft/

CircuitPython web workflow: http://esp-air.local/code/

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

- `settings.toml` (gitignored; copy `settings.toml.example`): Wi-Fi
  (`CIRCUITPY_WIFI_SSID`, `CIRCUITPY_WIFI_PASSWORD`), the board's name
  (`CIRCUITPY_WIFI_HOSTNAME`, `esp-air`; `code.py` also advertises it as
  `esp-air.local`, which the scripts use), web workflow
  (`CIRCUITPY_WEB_API_PASSWORD`, `CIRCUITPY_WEB_API_PORT`), altitude (`altitude`),
  sampling interval (`sampling_interval`), the recovery button (`button_pin`),
  InfluxDB (`db_host`, `db_port`, `db_database`, `db_table`, `db_username`,
  `db_password`), and Pushover (`pushover_user`, `pushover_token`) for the notifier.
- `boot.py`: hides the USB drive unless the recovery button is pressed (see below).
- `scripts/`, `package.json`: Node scripts behind the npm commands below.
- `thresholds.py`: caution and danger ranges for each metric, as half-open
  `(min, max)` pairs. Safe to commit.
- `code.py`: setup and the main loop.
- `reporters/`: `display.py`, `db.py`, `notifier.py`, `flaky.py` (a test reporter
  that fails a few times in a row, to exercise the error handling), and `log.py`
  (currently empty).
- `tests/` and `snippets/`: host-side tests and scratch code that isn't deployed.

TODO:
  - update notion, update hass stuff for the new hostname (esp-air)
	- get the notification reporter working
	- what about a reporter_manager class?
	- ask claude for other suggestions
	- update this file - as built

## Development workflow

Everything normally goes over Wi-Fi with web workflow, so `boot.py` hides the USB
drive (web workflow can only write files while a computer isn't mounting it).
Run `npm install` once, and `pipx install circup` for the dependency tasks. All of
these are VS Code tasks (**Terminal > Run Task**,
[.vscode/tasks.json](.vscode/tasks.json)):

- **deploy** (`npm run deploy`): copy `settings.toml`, `thresholds.py`, `boot.py`,
  `reporters/*.py` and `code.py` to the board at `<CIRCUITPY_WIFI_HOSTNAME>.local`.
  The password comes from your local `settings.toml`, which overwrites the board's
  copy. CircuitPython reloads as files land (you may see it restart a few times);
  `code.py` goes last. `boot.py` only takes effect after a reset. Doesn't copy
  `lib/`, snippets or tests, and doesn't delete files on the board.
- **fetch_from_board** (`npm run fetch-from-board`): copy files from the board to
  this directory, for when you edited with the web workflow code editor. Skips
  `lib/`. Then commit and push with git.
- **add_deps** / **install_deps**: circup over web workflow. `add_deps` installs the
  libraries `code.py` and the reporters import, then writes `requirements.txt`
  (review it; it lists everything on the board). `install_deps` installs from it
  onto a fresh board. To run any other circup command over web workflow:
  `npm run circup -- update --all`.
- **deploy_usb**, **add_deps_usb**, **install_deps_usb**: the same over a mounted
  `/Volumes/CIRCUITPY`, for recovery mode.

For initial setup: copy `settings.toml.example` to `settings.toml` and fill it in,
get the board into recovery mode (below), run `install_deps_usb` and `deploy_usb`,
then reset normally. After that, use the web workflow tasks. Back up private
configuration separately before firmware or bootloader upgrades.

For library updates: `npm run circup -- update --all`, test, then `add_deps` to
refresh `requirements.txt`. Circup picks compiled libraries for the board's
CircuitPython version; `lib/` in this repo is not deployed.

### Recovery mode (USB mass storage)

Tap RESET, then press and hold the button (`button_pin`, D1 by default) while the
NeoPixel is blue (about 3 seconds). It turns green and the `CIRCUITPY` drive shows
up. Holding it through the reset works too. While the drive is mounted on a
computer, web workflow can't write files (deploy reports a 409). Don't use D0 (BOOT)
held through a reset: that puts the chip in its ROM bootloader instead. If
`button_pin` is wrong, `boot.py` leaves USB enabled rather than locking you out.

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