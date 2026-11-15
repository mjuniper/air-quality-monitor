import microcontroller
from watchdog import WatchDogMode
import board
import digitalio
import neopixel
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
import time
# import wifi
import adafruit_sen6x
from thresholds import thresholds
from reporters.display import DisplayReporter
from reporters.db import InfluxDbReporter
# from reporters.flaky import FlakyReporter
# from reporters.notifier import NotificationReporter
# import gc

# TODO: we will probably want this to be something like 2 - 5 minutes
# but in development we want a shorter interval to better understand if it is working
sampling_interval = 30 * 1000
# sampling_interval = 5 * 1000

# Arm the watchdog BEFORE the sensor init, so a crash during boot also ends in a reset.
wdt = microcontroller.watchdog
wdt.timeout = max(60, 3 * sampling_interval / 1000)  # seconds; ~6 min at 2 min
wdt.mode = WatchDogMode.RESET
wdt.feed()

# check buttons at startup...
# hold D1 to calibrate scd30 based on eCO2 reading from the ens160
# calibrate_ambient = digitalio.DigitalInOut(board.D1)
# calibrate_ambient.switch_to_input(pull=digitalio.Pull.DOWN)
# hold D2 to calibrate scd30 based on a value of 425 which should approximate fresh outside air
# calibrate_outside = digitalio.DigitalInOut(board.D2)
# calibrate_outside.switch_to_input(pull=digitalio.Pull.DOWN)
# calibrate_scd = calibrate_ambient.value or calibrate_outside.value
# press button 0 to change display mode
change_display_mode = digitalio.DigitalInOut(board.D0)
change_display_mode.switch_to_input(pull=digitalio.Pull.UP)

# #####
# setup neopixel
# #####
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = .1

# #####
# setup reporters
# #####
reporters = []
# TODO: i could factor this into a reporter_manager class
display_reporter = DisplayReporter(thresholds)
reporters.append(display_reporter)
reporters.append(InfluxDbReporter())
# reporters.append(NotificationReporter(thresholds))
# reporters.append(FlakyReporter())

def report(data):
  for reporter in reporters:
    try:
      reporter.report(data)
      display_reporter.clearError(reporter.name)
    except Exception as e:
      display_reporter.logError(reporter.name, e)

# #####
# did the watchdog just restart us?
# #####
# A reset wipes the in-RAM error log, so without this we'd never know it
# happened. Log it now; it clears itself after the first good sensor read and
# then shows on the log page as "watchdog: ok for ...".
print("Reset reason:", microcontroller.cpu.reset_reason)
if microcontroller.cpu.reset_reason == microcontroller.ResetReason.WATCHDOG:
  display_reporter.logError("watchdog", "restarted after stall")

# #####
# setup to read sensors
# #####
stemma_i2c = board.STEMMA_I2C()

sensor = adafruit_sen6x.SEN66(stemma_i2c)
sensor.sensor_altitude = 1525
display_reporter.showMessage("Sensor initialized")
sensor.start_measurement()
# Note: CO2 values will be 0xFFFF for first 5-6 seconds after measurement start.
# Note: NOx values will be 0x7FFF for first 10-11 seconds after power-on/reset.
time.sleep(12)
display_reporter.showMessage("Measurement started")
time.sleep(3)

# #####
# loop!
# #####
sensor_clock = ticks_ms()
first_run = True
last_mode_change = time.time()
while True:
  if not change_display_mode.value and time.time() - last_mode_change > 0.8:
    display_reporter.incrementMode()
    last_mode_change = time.time()

  if first_run or ticks_diff(ticks_ms(), sensor_clock) > sampling_interval:

    pixel.fill((0, 255, 0))

    # #####
    # read the sensors
    # #####
    # TODO: we want to not bring the whole thing down when there is an error
    # this works for now but we can do better...
    # it would also be good to know how long it has been failing
    data = None
    try:
      if sensor.data_ready:
        sensor.check_sensor_errors()
        sensor_data = sensor.all_measurements()
        data = {
          "co2": sensor_data["co2"], # CO2 concentration in PPM
          "temp": sensor_data["temperature"], # current temperature in degrees C
          "hum": sensor_data["humidity"], # relative humidity in %rH
          "voc": sensor_data["voc_index"], # an index representing volatile organic compounds (VOC) level
          "nox": sensor_data["nox_index"], # an index representing nitrogen oxides (NOx) level
          "pm1": sensor_data["pm1_0"], 
          "pm25": sensor_data["pm2_5"], 
          "pm4": sensor_data["pm4_0"], 
          "pm10": sensor_data["pm10"],
        }
        display_reporter.clearError("sensor")
        display_reporter.clearError("watchdog")  # no-op unless we just restarted
        wdt.feed()
      else:
        raise RuntimeError("sensor data not ready")
    except Exception as e:
      display_reporter.logError("sensor", e)

    if data is not None:
      report(data)

    pixel.fill((255, 0, 0) if display_reporter.has_errors else (0, 0, 0))

    # i think i have a memory leak... or maybe that is just the way python works???
    # free memory continuously falls with every iteration of the loop until it gets down to a few k
    # then it goes back up - presumably because garbage collection happened
    # if i manually do garbage collection as below, it stays high
    # but i think we will let garbage collection happen on its own
    # gc.collect())

    sensor_clock = ticks_add(sensor_clock, sampling_interval)

    if first_run:
      sensor_clock = ticks_ms()
      first_run = False