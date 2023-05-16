import board
import terminalio
import displayio
from adafruit_display_text import bitmap_label, wrap_text_to_pixels

# https://learn.adafruit.com/circuitpython-display-support-using-displayio/introduction
# https://learn.adafruit.com/circuitpython-display_text-library/overview
# https://learn.adafruit.com/adafruit-1-14-240x135-color-tft-breakout/circuitpython-displayio-quickstart

# https://learn.adafruit.com/aqi-case/coding-the-aqi-case

# colors for various statuses:
# https://www.rapidtables.com/web/color/green-color.html
# https://www.rapidtables.com/web/color/orange-color.html
# https://www.rapidtables.com/web/color/red-color.html

# Display modes:
#   0. voc, pm25, co2
#   1. temp, hum
#   2. co2, eco2
#   3. pm25, pm10, pm100
#   4. voc, aqi
#   5. error log

green = 0x00FA9A #0x00FFFF 0x228B22
yellow = 0xFFA500
red = 0xFF0000

class DisplayReporter:

  def __init__(self, params):
    self.thresholds = params['thresholds']

    board.DISPLAY.brightness = 0.6
    self.display_mode = 0
  
    self.message_text_area = bitmap_label.Label(terminalio.FONT, text="", scale=2)
    self.message_text_area.anchor_point = (0.5, 0.5)
    self.message_text_area.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height // 2)
    self.message_text_area.color = green
    board.DISPLAY.show(self.message_text_area)

    # groups for the various modes
    self.reporter_group_0 = displayio.Group()
    self.reporter_group_1 = displayio.Group()
    self.reporter_group_2 = displayio.Group()
    self.reporter_group_3 = displayio.Group()
    self.reporter_group_4 = displayio.Group()
    self.reporter_groups = (self.reporter_group_0, self.reporter_group_1, self.reporter_group_2, self.reporter_group_3, self.reporter_group_4)

    # tuples to hold labels for various data
    self.co2_labels = []
    self.voc_labels = []
    self.aqi_labels = []
    self.pm25_labels = []
    self.pm10_labels = []
    self.pm100_labels = []
    self.temp_labels = []
    self.hum_labels = []
    self.eco2_labels = []

    padding = 36

    # reporter_group_0
    pm2_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    pm2_value.anchor_point = (0.5, 0)
    pm2_value.anchored_position = (40, padding)
    pm2_label = bitmap_label.Label(terminalio.FONT, text="PM 2.5", scale=2)
    pm2_label.anchor_point = (0.5, 1)
    pm2_label.anchored_position = (40, board.DISPLAY.height - padding)
    self.pm25_labels.append((pm2_label, pm2_value))

    voc_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    voc_value.anchor_point = (0.5, 0)
    voc_value.anchored_position = (board.DISPLAY.width // 2, padding)
    voc_label = bitmap_label.Label(terminalio.FONT, text="VOC", scale=2, padding_bottom=padding)
    voc_label.anchor_point = (0.5, 1)
    voc_label.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height - padding)
    self.voc_labels.append((voc_label, voc_value))

    co2_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3, padding_top=padding)
    co2_value.anchor_point = (0.5, 0)
    co2_value.anchored_position = (200, padding)
    co2_label = bitmap_label.Label(terminalio.FONT, text="CO2", scale=2, padding_bottom=padding)
    co2_label.anchor_point = (0.5, 1)
    co2_label.anchored_position = (200, board.DISPLAY.height - padding)
    self.co2_labels.append((co2_label, co2_value))
    
    self.reporter_group_0.append(pm2_value)
    self.reporter_group_0.append(pm2_label)
    self.reporter_group_0.append(voc_value)
    self.reporter_group_0.append(voc_label)
    self.reporter_group_0.append(co2_value)
    self.reporter_group_0.append(co2_label)

    # reporter_group_1
    temp_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    temp_value.anchor_point = (0.5, 0)
    temp_value.anchored_position = (60, padding)
    temp_label = bitmap_label.Label(terminalio.FONT, text="TEMP", scale=2)
    temp_label.anchor_point = (0.5, 1)
    temp_label.anchored_position = (60, board.DISPLAY.height - padding)
    self.temp_labels.append((temp_label, temp_value))

    hum_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3, padding_top=padding)
    hum_value.anchor_point = (0.5, 0)
    hum_value.anchored_position = (180, padding)
    hum_label = bitmap_label.Label(terminalio.FONT, text="HUM", scale=2, padding_bottom=padding)
    hum_label.anchor_point = (0.5, 1)
    hum_label.anchored_position = (180, board.DISPLAY.height - padding)
    self.hum_labels.append((hum_label, hum_value))
    
    self.reporter_group_1.append(temp_value)
    self.reporter_group_1.append(temp_label)
    self.reporter_group_1.append(hum_value)
    self.reporter_group_1.append(hum_label)

    # reporter_group_2
    co2_value_2 = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    co2_value_2.anchor_point = (0.5, 0)
    co2_value_2.anchored_position = (60, padding)
    co2_label_2 = bitmap_label.Label(terminalio.FONT, text="CO2", scale=2)
    co2_label_2.anchor_point = (0.5, 1)
    co2_label_2.anchored_position = (60, board.DISPLAY.height - padding)
    self.co2_labels.append((co2_label_2, co2_value_2))

    eco2_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3, padding_top=padding)
    eco2_value.anchor_point = (0.5, 0)
    eco2_value.anchored_position = (180, padding)
    eco2_label = bitmap_label.Label(terminalio.FONT, text="eCO2", scale=2, padding_bottom=padding)
    eco2_label.anchor_point = (0.5, 1)
    eco2_label.anchored_position = (180, board.DISPLAY.height - padding)
    self.eco2_labels.append((eco2_label, eco2_value))
    
    self.reporter_group_2.append(co2_value_2)
    self.reporter_group_2.append(co2_label_2)
    self.reporter_group_2.append(eco2_value)
    self.reporter_group_2.append(eco2_label)

    # reporter_group_3
    pm2_value_2 = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    pm2_value_2.anchor_point = (0.5, 0)
    pm2_value_2.anchored_position = (40, padding)
    pm2_label_2 = bitmap_label.Label(terminalio.FONT, text="PM 2.5", scale=2)
    pm2_label_2.anchor_point = (0.5, 1)
    pm2_label_2.anchored_position = (40, board.DISPLAY.height - padding)
    self.pm25_labels.append((pm2_label_2, pm2_value_2))

    pm10_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    pm10_value.anchor_point = (0.5, 0)
    pm10_value.anchored_position = (board.DISPLAY.width // 2, padding)
    pm10_label = bitmap_label.Label(terminalio.FONT, text="PM 10", scale=2, padding_bottom=padding)
    pm10_label.anchor_point = (0.5, 1)
    pm10_label.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height - padding)
    self.pm25_labels.append((pm10_label, pm10_value))

    pm100_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3, padding_top=padding)
    pm100_value.anchor_point = (0.5, 0)
    pm100_value.anchored_position = (200, padding)
    pm100_label = bitmap_label.Label(terminalio.FONT, text="PM 100", scale=2, padding_bottom=padding)
    pm100_label.anchor_point = (0.5, 1)
    pm100_label.anchored_position = (200, board.DISPLAY.height - padding)
    self.pm25_labels.append((pm100_label, pm100_value))
    
    self.reporter_group_3.append(pm2_value_2)
    self.reporter_group_3.append(pm2_label_2)
    self.reporter_group_3.append(pm10_value)
    self.reporter_group_3.append(pm10_label)
    self.reporter_group_3.append(pm100_value)
    self.reporter_group_3.append(pm100_label)

    # reporter_group_4
    voc_value_2 = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    voc_value_2.anchor_point = (0.5, 0)
    voc_value_2.anchored_position = (60, padding)
    voc_label_2 = bitmap_label.Label(terminalio.FONT, text="VOC", scale=2)
    voc_label_2.anchor_point = (0.5, 1)
    voc_label_2.anchored_position = (60, board.DISPLAY.height - padding)
    self.voc_labels.append((voc_label_2, voc_value_2))

    aqi_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3, padding_top=padding)
    aqi_value.anchor_point = (0.5, 0)
    aqi_value.anchored_position = (180, padding)
    aqi_label = bitmap_label.Label(terminalio.FONT, text="AQI", scale=2, padding_bottom=padding)
    aqi_label.anchor_point = (0.5, 1)
    aqi_label.anchored_position = (180, board.DISPLAY.height - padding)
    self.aqi_labels.append((aqi_label, aqi_value))
    
    self.reporter_group_4.append(voc_value_2)
    self.reporter_group_4.append(voc_label_2)
    self.reporter_group_4.append(aqi_value)
    self.reporter_group_4.append(aqi_label)

  def _showMessage (self, msg, color):
    self.message_text_area.color = color

    lines = wrap_text_to_pixels(msg, board.DISPLAY.width // 2, terminalio.FONT)
    formatted_message = '\n'.join(lines)

    self.message_text_area.text = formatted_message
    board.DISPLAY.show(self.message_text_area)
    print(formatted_message + '\n')

  def showMessage (self, msg):
    self._showMessage(msg, green)

  def showError (self, msg):
    self._showMessage(msg, red)

  def getColor (self, value, caution_threshold, danger_threshold):
    # threshold looks like: ((min, max), (min, max), ...)
    color = green

    for range in caution_threshold:
      if value >= range[0] and value < range[1]:
        color = yellow

    for range in danger_threshold:
      if value >= range[0] and value < range[1]:
        color = red

    return color
  
  def setValues(self, labels, value, color):
    for pair in labels:
      pair[1].text = str(value)
      for label in pair:
        label.color = color

  def incrementMode(self):
    display_mode = self.display_mode + 1
    if display_mode >= len(self.reporter_groups):
      display_mode = 0
    self.display_mode = display_mode
    board.DISPLAY.show(self.reporter_groups[self.display_mode])

  def report(self, data):
    try:
      pm25 = data["pm25"]
      pm2_color = self.getColor(pm25, self.thresholds["pm25_caution"], self.thresholds["pm25_danger"])
      self.setValues(self.pm25_labels, pm25, pm2_color)

      pm10 = data["pm10"]
      pm10_color = self.getColor(pm10, self.thresholds["pm25_caution"], self.thresholds["pm25_danger"])
      self.setValues(self.pm10_labels, pm10, pm10_color)

      pm100 = data["pm100"]
      pm100_color = self.getColor(pm100, self.thresholds["pm25_caution"], self.thresholds["pm25_danger"])
      self.setValues(self.pm100_labels, pm100, pm100_color)

      voc = data["voc"]
      voc_color = self.getColor(voc, self.thresholds["voc_caution"], self.thresholds["voc_danger"])
      self.setValues(self.voc_labels, voc, voc_color)

      aqi = data["aqi"]
      aqi_color = self.getColor(aqi, self.thresholds["aqi_caution"], self.thresholds["aqi_danger"])
      self.setValues(self.aqi_labels, aqi, aqi_color)

      eco2 = data["eco2"]
      eco2_color = self.getColor(eco2, self.thresholds["co2_caution"], self.thresholds["co2_danger"])
      self.setValues(self.eco2_labels, "%.0f" % (eco2), eco2_color)

      co2 = data["co2"]
      co2_color = self.getColor(co2, self.thresholds["co2_caution"], self.thresholds["co2_danger"])
      self.setValues(self.co2_labels, "%.0f" % (co2), co2_color)

      temp = data["temp"] * 1.8 + 32
      temp_color = self.getColor(temp, self.thresholds["temp_caution"], self.thresholds["temp_danger"])
      self.setValues(self.temp_labels, "%.1f" % (temp), temp_color)

      hum = data["hum"]
      hum_color = self.getColor(hum, self.thresholds["hum_caution"], self.thresholds["hum_danger"])
      self.setValues(self.hum_labels, "%.1f" % (hum), hum_color)

      board.DISPLAY.show(self.reporter_groups[self.display_mode])

    except Exception as e:
      print('DisplayReporter error: ' + str(e))
