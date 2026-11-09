import wifi
import ssl
import socketpool
import adafruit_requests

class InfluxDbReporter:

  def __init__(self, secrets):
    self.host = secrets['db']['host']
    self.port = secrets['db']['port']
    self.database = secrets['db']['database']
    self.table = secrets['db']['table']
    self.username = secrets['db']['username']
    self.password = secrets['db']['password']

    self.table = secrets['db']['table']

    
    pool = socketpool.SocketPool(wifi.radio)
    self.session = adafruit_requests.Session(pool, ssl.create_default_context())
    
  def report(self, data):
    if not wifi.radio.connected or wifi.radio.ipv4_address is None:
      print('InfluxDbReporter: skipping report; Wi-Fi is not connected.')
      return

    try:
      # influxdb "line protocol"
      # https://docs.influxdata.com/influxdb/v1.8/guides/write_data/#write-data-using-the-influxdb-api
      point = self.table + " " + ','.join(f'{k}={v}' for k,v in data.items())
      url = f"http://{self.host}:{self.port}/write?db={self.database}"
      # print(url)

      headers = {"Authorization": f"Token {self.username}:{self.password}"}
      # headers.setdefault('Content-Type', 'application/octet-stream')
      # headers.setdefault('Accept', 'application/x-msgpack')

      response = self.session.post(url, data=point, headers=headers, timeout=10)
      try:
        if not 200 <= response.status_code < 300:
          print('InfluxDbReporter error: HTTP ' + str(response.status_code))
      finally:
        response.close()
    except Exception as e:
      print('InfluxDbReporter error: ' + str(e))
