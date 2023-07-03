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