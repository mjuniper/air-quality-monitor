# reporters/db.py
#
# Sends sensor readings to InfluxDB 1.x over HTTP using line protocol.
# Reads connection info from settings.toml via os.getenv().

import os
import ssl
import wifi
import socketpool
import adafruit_requests

class InfluxDbReporter:

  def __init__(self):
    self.name = "influx"

    self.host = os.getenv("db_host")
    self.port = os.getenv("db_port")
    self.database = os.getenv("db_database")
    self.table = os.getenv("db_table")
    self.username = os.getenv("db_username")
    self.password = os.getenv("db_password")

    # The HTTP session is created lazily by ensure_wifi(). None means
    # "no usable session right now".
    self.session = None
    self.ensure_wifi()

  def _make_session(self):
    # A session wraps a socket pool tied to the current Wi-Fi connection.
    # If Wi-Fi drops, the old pool and its sockets are stale, so we rebuild.
    pool = socketpool.SocketPool(wifi.radio)
    self.session = adafruit_requests.Session(pool, ssl.create_default_context())

  def ensure_wifi(self):
    # Make sure we're on Wi-Fi and have a live session. Returns True if so.
    try:
      if not wifi.radio.connected:
        wifi.radio.connect(
          os.getenv("CIRCUITPY_WIFI_SSID"),
          os.getenv("CIRCUITPY_WIFI_PASSWORD"),
        )
        # We just (re)connected, so any old session is dead.
        self.session = None

      # Covers both first boot (CircuitPython may have auto-connected from
      # settings.toml before we ran) and the post-reconnect case above.
      if self.session is None:
        self._make_session()

      return True
    except Exception as e:
      print("InfluxDbReporter: WiFi/session setup failed: " + str(e))
      self.session = None
      return False

  def report(self, data):
    if not self.ensure_wifi():
      raise RuntimeError("Wi-Fi not connected")
    try:
      # Influx line protocol: "<measurement> field=value,field=value"
      # https://docs.influxdata.com/influxdb/v1.8/guides/write_data/#write-data-using-the-influxdb-api
      #
      # Skip None (and NaN, which is the only value not equal to itself).
      # A single bad value makes Influx reject the whole line.
      fields = ",".join(
        f"{k}={v}" for k, v in data.items() if v is not None and v == v
      )
      if not fields:
        print("InfluxDbReporter: no valid fields to report.")
        return

      point = self.table + " " + fields
      url = f"http://{self.host}:{self.port}/write?db={self.database}"
      headers = {"Authorization": f"Token {self.username}:{self.password}"}

      response = self.session.post(url, data=point, headers=headers, timeout=5)
      try:
        if not 200 <= response.status_code < 300:
          raise RuntimeError("HTTP " + str(response.status_code))
      finally:
        response.close()
    except Exception:
      self.session = None  # rebuild next time
      raise
  
  # def report(self, data):
  #   if not self.ensure_wifi():
  #     print("InfluxDbReporter: skipping report; Wi-Fi is not connected.")
  #     return

  #   try:
  #     # Influx line protocol: "<measurement> field=value,field=value"
  #     # https://docs.influxdata.com/influxdb/v1.8/guides/write_data/#write-data-using-the-influxdb-api
  #     #
  #     # Skip None (and NaN, which is the only value not equal to itself).
  #     # A single bad value makes Influx reject the whole line.
  #     fields = ",".join(
  #       f"{k}={v}" for k, v in data.items() if v is not None and v == v
  #     )
  #     if not fields:
  #       print("InfluxDbReporter: no valid fields to report.")
  #       return

  #     point = self.table + " " + fields
  #     url = f"http://{self.host}:{self.port}/write?db={self.database}"
  #     headers = {"Authorization": f"Token {self.username}:{self.password}"}

  #     response = self.session.post(url, data=point, headers=headers, timeout=5)
  #     try:
  #       if not 200 <= response.status_code < 300:
  #         print("InfluxDbReporter error: HTTP " + str(response.status_code))
  #     finally:
  #       # Always close, or sockets leak and you eventually run out.
  #       response.close()

  #   except Exception as e:
  #     print("InfluxDbReporter error: " + str(e))
  #     # Drop the session so the next report rebuilds it from scratch.
  #     self.session = None