#import http.client, urllib
import time
import wifi
import ssl
import socketpool
import adafruit_requests

class NotificationReporter:

  lastNotification = 0

  def __init__(self, params):
    self.threshold = params['threshold']
    self.token = params['pushovertoken']
    self.user = params['pushoveruser']
    
    pool = socketpool.SocketPool(wifi.radio)
    self.session = adafruit_requests.Session(pool, ssl.create_default_context())

  def sendNotification (self, msg):
    data = {
      "token": self.token,
      "user": self.user,
      "message": msg,
    }
    response = self.session.post("https://api.pushover.net:443/1/messages.json", json=data)

  def shouldSendNotification (self):
    # we want to only send a notification once a day
    now = time.time()
    if now - self.lastNotification > 86400:
      self.lastNotification = now;
      return True
    return False
    
  def report(self, data):
    try:
      delta = data["delta"]
      if delta >= (self.threshold * -1) and self.shouldSendNotification():
        self.sendNotification(f"Radon mitigation system is outside expected pressure differential {delta}.")
    except Exception as e:
      print('NotificationReporter error: ' + str(e))