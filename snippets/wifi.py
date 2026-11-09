
import board
import digitalio
import time
import neopixel

# print("Hello World....")

# SPDX-FileCopyrightText: 2020 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import ipaddress
import ssl
import wifi
import socketpool
import adafruit_requests

# URLs to fetch from
# TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
# JSON_QUOTES_URL = "https://www.adafruit.com/api/quotes.php"
# JSON_STARS_URL = "https://api.github.com/repos/adafruit/circuitpython"

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print()
print("ESP32-S2 WebClient Test")
print()

# print("My MAC addr:", [hex(i) for i in wifi.radio.mac_address])

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])
print()

print("My IP address is", wifi.radio.ipv4_address)

ipv4 = ipaddress.ip_address("8.8.4.4")
print("Ping google.com: %f ms" % (wifi.radio.ping(ipv4) * 1000))

# pool = socketpool.SocketPool(wifi.radio)
# requests = adafruit_requests.Session(pool, ssl.create_default_context())

# print("Fetching text from", TEXT_URL)
# response = requests.get(TEXT_URL)
# print("-" * 40)
# print(response.text)
# print("-" * 40)

# print("Fetching json from", JSON_QUOTES_URL)
# response = requests.get(JSON_QUOTES_URL)
# print("-" * 40)
# print(response.json())
# print("-" * 40)

# print()

# print("Fetching and parsing json from", JSON_STARS_URL)
# response = requests.get(JSON_STARS_URL)
# print("-" * 40)
# print("CircuitPython GitHub Stars", response.json()["stargazers_count"])
# print("-" * 40)

print()
print("done")

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.2

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

while True:
    led.value = True
    pixel.fill((0, 0, 0))
    time.sleep(0.2)
    led.value = False
    pixel.fill((0, 0, 255))
    time.sleep(0.5)