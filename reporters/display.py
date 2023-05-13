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
#   1. voc, pm25, co2
#   2. pm25, pm10, pm100
#   3. voc, aqi
#   4. co2, eco2
#   5. error log

green = 0x00FA9A #0x00FFFF 0x228B22
yellow = 0xFFA500
red = 0xFF0000

class DisplayReporter:

  def __init__(self, params):
    self.thresholds = params['thresholds']
  
    self.message_text_area = bitmap_label.Label(terminalio.FONT, text="", scale=2)
    self.message_text_area.anchor_point = (0.5, 0.5)
    self.message_text_area.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height // 2)
    self.message_text_area.color = green
    board.DISPLAY.brightness = 0.6
    board.DISPLAY.show(self.message_text_area)

    # top level groups for the various modes
    self.reporter_group_1 = displayio.Group()
    # self.reporter_group_2 = displayio.Group()
    # self.reporter_group_3 = displayio.Group()

    padding = 36

    # groups for each data element
    self.pm2_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    self.pm2_value.anchor_point = (0.5, 0)
    self.pm2_value.anchored_position = (40, padding)
    self.pm2_label = bitmap_label.Label(terminalio.FONT, text="PM 2.5", scale=2)
    self.pm2_label.anchor_point = (0.5, 1)
    self.pm2_label.anchored_position = (40, board.DISPLAY.height - padding)

    self.voc_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3)
    self.voc_value.anchor_point = (0.5, 0)
    self.voc_value.anchored_position = (board.DISPLAY.width // 2, padding)
    self.voc_label = bitmap_label.Label(terminalio.FONT, text="VOC", scale=2, padding_bottom=padding)
    self.voc_label.anchor_point = (0.5, 1)
    self.voc_label.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height - padding)

    self.co2_value = bitmap_label.Label(terminalio.FONT, text="000", scale=3, padding_top=padding)
    self.co2_value.anchor_point = (0.5, 0)
    self.co2_value.anchored_position = (200, padding)
    self.co2_label = bitmap_label.Label(terminalio.FONT, text="CO2", scale=2, padding_bottom=padding)
    self.co2_label.anchor_point = (0.5, 1)
    self.co2_label.anchored_position = (200, board.DISPLAY.height - padding)
    
    self.reporter_group_1.append(self.pm2_value)
    self.reporter_group_1.append(self.pm2_label)
    self.reporter_group_1.append(self.voc_value)
    self.reporter_group_1.append(self.voc_label)
    self.reporter_group_1.append(self.co2_value)
    self.reporter_group_1.append(self.co2_label)

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
  
  def report(self, data):
    try:
      pm2 = data["pm25"]
      self.pm2_value.text = str(pm2)
      pm2_color = self.getColor(pm2, self.thresholds["pm25_caution"], self.thresholds["pm25_danger"])
      self.pm2_value.color = pm2_color
      self.pm2_label.color = pm2_color

      voc = data["voc"]
      self.voc_value.text = str(voc)
      voc_color = self.getColor(voc, self.thresholds["voc_caution"], self.thresholds["voc_danger"])
      self.voc_value.color = voc_color
      self.voc_label.color = voc_color

      co2 = data["co2"]
      self.co2_value.text = "%.0f" % (co2)
      co2_color = self.getColor(co2, self.thresholds["co2_caution"], self.thresholds["co2_danger"])
      self.co2_value.color = co2_color
      self.co2_label.color = co2_color

      board.DISPLAY.show(self.reporter_group_1)

    except Exception as e:
      print('DisplayReporter error: ' + str(e))
