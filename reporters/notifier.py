import os
import time
import wifi
import ssl
import socketpool
import adafruit_requests

class NotificationReporter:

  lastNotification = 0

  def __init__(self, thresholds):
    self.threshold = thresholds
    self.user = os.getenv("pushover_user")
    self.token = os.getenv("pushover_token")
    
    pool = socketpool.SocketPool(wifi.radio)
    self.session = adafruit_requests.Session(pool, ssl.create_default_context())

  def sendNotification (self, msg):
    if not wifi.radio.connected or wifi.radio.ipv4_address is None:
      print('NotificationReporter: skipping notification; Wi-Fi is not connected.')
      return

    data = {
      "token": self.token,
      "user": self.user,
      "message": msg,
    }
    response = self.session.post(
      "https://api.pushover.net:443/1/messages.json", json=data, timeout=10
    )
    try:
      if response.status_code != 200:
        print('NotificationReporter error: HTTP ' + str(response.status_code))
        return
      if response.json().get("status") != 1:
        print('NotificationReporter error: Pushover did not accept the notification.')
        return
      self.lastNotification = time.time()
    finally:
      response.close()

  def shouldSendNotification (self):
    # we want to only send a notification once a day
    now = time.time()
    if now - self.lastNotification > 86400:
      return True
    return False
    
  def report(self, data):
    try:
      delta = data["delta"]
      if delta >= (self.threshold * -1) and self.shouldSendNotification():
        self.sendNotification(f"Radon mitigation system is outside expected pressure differential {delta}.")
    except Exception as e:
      print('NotificationReporter error: ' + str(e))