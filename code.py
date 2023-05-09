import board
import busio
import digitalio
import neopixel
import time
import wifi
from adafruit_pm25.i2c import PM25_I2C
import adafruit_scd30
import adafruit_ens160
from secrets import secrets
from reporters.display import DisplayReporter
from reporters.db import InfluxDbReporter
# from reporters.notifier import NotificationReporter
# import gc

# TODO:
#   - get display reporter working better
#     - start with just writing the most important data in a nice readable way
#     - make use of thresholds
#     - create (3?) different display modes that display different data
#   - get the notification reporter working
#     - make use of thresholds
#   - review TODOs
#   - use asyncio (or something) to make it respond to button presses by changing the display mode
#   - refactor...
#   - in an effort to make it resilient, i transiently write some errors to the screen
#      and others i only ever print to the serial console... it would be nice to log errors somehow
#      and print something persistently to the screen to indicate that i should check those logs

# TODO: we will probably want this to be something like 2 - 5 minutes
# but in development we want a shorter interval to better understand if it is working
sampling_interval = 2 * 60
# sampling_interval = 30

# check buttons at startup...
# hold D1 to calibrate scd30 based on eCO2 reading from the ens160
calibrate_ambient = digitalio.DigitalInOut(board.D1)
calibrate_ambient.switch_to_input(pull=digitalio.Pull.DOWN)
# hold D2 to calibrate scd30 based on a value of 425 which should approximate fresh outside air
calibrate_outside = digitalio.DigitalInOut(board.D2)
calibrate_outside.switch_to_input(pull=digitalio.Pull.DOWN)
calibrate_scd = calibrate_ambient.value or calibrate_outside.value

# #####
# setup neopixel
# #####
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = .6

# #####
# setup reporters
# #####
reporters = []
# TODO: set up the reporters appropriately
# TODO: i could factor this into a reporter_manager class
display_reporter = DisplayReporter(secrets)
reporters.append(display_reporter)
reporters.append(InfluxDbReporter(secrets))
# reporters.append(NotificationReporter(secrets))

def report(data):
  if data["co2"] != None and data["co2"] > 400 and data["aqi"] != None and data["aqi"] > 0 and data["eco2"] != None and data["eco2"] > 0:
    for reporter in reporters:
      reporter.report(data)
  else:
    display_reporter.showError("Skipping reporting data\nbecause it seems bogus.")

# #####
# connect to the network
# #####
display_reporter.showMessage("Connecting to\n%s" % secrets["wifi"]["ssid"])
try:
  wifi.radio.connect(secrets["wifi"]["ssid"], secrets["wifi"]["password"])
except Exception as e:
  display_reporter.showMessage("Error connecting\nto network: " + str(e))

display_reporter.showMessage("Connected to\n%s!" % secrets["wifi"]["ssid"])

time.sleep(2)

# #####
# setup to read sensors
# #####
# the pm25 sensor docs suggest using 100khz frequency...
# stemma_i2c = board.STEMMA_I2C(frequency=100000)
# but that seems to be the default
# stemma_i2c = board.STEMMA_I2C()
# one of the others suggests even slower
# TODO: what does frequency even mean in this context?
stemma_i2c = busio.I2C(board.SCL, board.SDA, frequency=50000)

# TODO: setup the sensors
# Connect to a PM2.5 sensor over I2C
pm25 = PM25_I2C(stemma_i2c)
# read with pm25.read()
# see https://learn.adafruit.com/pmsa003i/python-circuitpython

# connect to voc sensor over I2C
ens = adafruit_ens160.ENS160(stemma_i2c)
# see https://learn.adafruit.com/adafruit-ens160-mox-gas-sensor/circuitpython-python

# connect to scd30 over I2C
scd = adafruit_scd30.SCD30(stemma_i2c)
# setup scd30 params
# we check the values first because the non-volatile memory that stores this stuff may have a limited number of writes
if scd.self_calibration_enabled != False:
  scd.self_calibration_enabled = False
if scd.measurement_interval != sampling_interval:
  scd.measurement_interval = sampling_interval
if scd.altitude != 1538:
  scd.altitude = 1538
# it might be even better to set scd.ambient_pressure but i don't have a pressure sensor hooked up...
if scd.ambient_pressure != 0:
  scd.ambient_pressure = 0

if calibrate_scd:
  # https://www.sensirion.com/media/documents/33C09C07/620638B8/Sensirion_SCD30_Field_Calibration.pdf
  display_reporter.showMessage('Waiting to calibrate scd30...')
  time.sleep(2 * 60)
  # use the scd30 to calibrate the ens160
  if calibrate_ambient:
    if scd.temperature != None:
      ens.temperature_compensation = scd.temperature
    if scd.relative_humidity != None:
      ens.humidity_compensation = scd.relative_humidity
    # then use the ens160 to calibrate the scd30
    scd.forced_recalibration_reference = ens.eCO2
  else:
    # or we could just expose it to fresh air and use 425
    scd.forced_recalibration_reference = 425
  
  display_reporter.showMessage('Calibrated scd30!')
  time.sleep(2)

# TODO: do i need to worry about data_available?
# TODO: do i need to ignore the first co2 reading?
# see https://learn.adafruit.com/adafruit-scd30/python-circuitpython

scd_params = {
    "forced_recalibration_reference": scd.forced_recalibration_reference,
    "altitude": scd.altitude,
    "ambient_pressure": scd.ambient_pressure,
    "measurement_interval": scd.measurement_interval,
    "self_calibration_enabled": scd.self_calibration_enabled
  }
msg = '\n'.join(f'{k}={v}' for k,v in scd_params.items())
display_reporter.showMessage(msg)

time.sleep(15)

# #####
# loop!
# #####
while True:
  pixel.fill((0, 255, 0))

  # #####
  # check the network?
  # todo: if we don't have network, print that info to screen and make sure it stays there...
  # #####

  # #####
  # update sensor calibration
  # #####
  # TODO: we want to not bring the whole thing down when there is an error
  # this works for now but we can do better...
  try:
    ens.temperature_compensation = scd.temperature
    ens.humidity_compensation = scd.relative_humidity
  except Exception as e:
    display_reporter.showError('Error calibrating ens160: ' + str(e))

  # #####
  # read the sensors
  # #####
  # TODO: read the sensors - i think we should collect absolutely everything...
  # TODO: we want to not bring the whole thing down when there is an error
  # this works for now but we can do better...
  # if only one sensor fails, we should read and report the others
  # it would also be good to know how long it has been failing
  try:
    pm25_data = pm25.read()
    data = {
      # "data_available": scd.data_available,
      "co2": scd.CO2, # CO2 concentration in PPM
      "temp": scd.temperature, # current temperature in degrees C
      "hum": scd.relative_humidity, # relative humidity in %rH
      "aqi": ens.AQI, # air quality index: 1 - 5
      "voc": ens.TVOC, # ppb
      "pm25": pm25_data["pm25 env"],
      "eco2": ens.eCO2,
      # the above are the main ones we are interested in
      # but we'll keep these too:
      "pm10": pm25_data["pm10 env"],
      "pm100": pm25_data["pm100 env"],
      "particles_03um": pm25_data["particles 03um"],
      "particles_05um": pm25_data["particles 05um"],
      "particles_10um": pm25_data["particles 10um"],
      "particles_25um": pm25_data["particles 25um"],
      "particles_50um": pm25_data["particles 50um"],
      "particles_100um": pm25_data["particles 100um"]
    }
  except Exception as e:
    display_reporter.showError('Error reading sensors: ' + str(e))

  # #####
  # send data to appropriate places (influxdb, the screen, a log file, an alert to my phone)
  report(data)
  # #####

  pixel.fill((0, 0, 0))

  # i think i have a memory leak... or maybe that is just the way python works???
  # free memory continuously falls with every iteration of the loop until it gets down to a few k
  # then it goes back up - presumably because garbage collection happened
  # if i manually do garbage collection as below, it stays high
  # but i think we will let garbage collection happen on its own
  # gc.collect()

  time.sleep(sampling_interval)