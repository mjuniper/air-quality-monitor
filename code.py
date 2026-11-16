import microcontroller
from watchdog import WatchDogMode
import board
import keypad
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
import gc

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
# keypad.Keys scans the pin in the background, debounces it, and queues press
# events. That means one event per press (nothing repeats while held) and presses
# aren't lost when the loop is busy, e.g. blocked on a slow network request.
keys = keypad.Keys((board.D0,), value_when_pressed=False, pull=True)

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

# The sensor's error flags are "sticky" and the sensor keeps power across our own
# resets (watchdog, code reload), so clear any left over from before. If a real
# fault persists, the sensor sets them again on its own.
try:
  sensor.clear_device_status()
except Exception as e:
  print("clear_device_status failed: " + str(e))

# #####
# loop!
# #####
# Track when the next sample is DUE rather than when the last one happened.
# Starting it at "now" makes the first pass through the loop sample right away,
# so we don't sit on the boot message for a whole interval (and the watchdog
# gets its first feed sooner).
next_sample = ticks_ms()
while True:
  event = keys.events.get()
  if event and event.pressed:
    display_reporter.incrementMode()

  # ticks_diff handles the ticks counter wrapping around; >= 0 means "due".
  if ticks_diff(ticks_ms(), next_sample) >= 0:

    pixel.fill((0, 255, 0))

    # #####
    # read the sensors
    # #####
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
      # Sticky flags stay set after the problem goes away until cleared. Clear
      # them so the next read reflects the current state, not a stale flag.
      # If the fault is real, the sensor sets them again.
      try:
        sensor.clear_device_status()
      except Exception as clear_error:
        print("clear_device_status failed: " + str(clear_error))

    if data is not None:
      report(data)

    pixel.fill((255, 0, 0) if display_reporter.has_errors else (0, 0, 0))

    # Collect garbage ourselves once per cycle instead of waiting for the heap to
    # run low. Free memory falling to a few KB and then jumping back up is normal
    # CircuitPython behavior (garbage piles up until a collection is forced), not
    # a leak. Collecting on our own schedule is still better:
    #   - it happens at a time we choose, right after reporting, instead of
    #     automatically in the middle of the next HTTP request or display update
    #   - it limits heap fragmentation: a big allocation (HTTP/SSL buffers, a
    #     label redraw) can fail even with lots of free RAM if that RAM is
    #     scattered in small pieces
    #   - it's cheap: a few ms once per sampling interval
    gc.collect()

    # Schedule from now, not from the previous due time, so a slow cycle (say a
    # network timeout) just pushes the next sample out instead of triggering a
    # burst of catch-up samples.
    next_sample = ticks_add(ticks_ms(), sampling_interval)

  # Don't spin flat out between checks; saves power and heat next to the sensor.
  time.sleep(0.02)