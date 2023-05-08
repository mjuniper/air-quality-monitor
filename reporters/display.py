import board
import terminalio
# import displayio
from adafruit_display_text import bitmap_label, wrap_text_to_lines

# https://learn.adafruit.com/circuitpython-display-support-using-displayio/introduction
# https://learn.adafruit.com/circuitpython-display_text-library/overview
# https://learn.adafruit.com/adafruit-1-14-240x135-color-tft-breakout/circuitpython-displayio-quickstart

# colors for various statuses:
# https://www.rapidtables.com/web/color/green-color.html
# https://www.rapidtables.com/web/color/orange-color.html
# https://www.rapidtables.com/web/color/red-color.html

class DisplayReporter:

  def __init__(self, params):
    # self.threshold = params['threshold']
  
    scale = 1
    self.text_area = bitmap_label.Label(terminalio.FONT, text="", scale=scale)
    self.text_area.anchor_point = (0.5, 0.5)
    self.text_area.anchored_position = (board.DISPLAY.width // 2, board.DISPLAY.height // 2)
    self.text_area.color = 0x00FFFF
    # self.text_area.line_spacing = 1.25
    board.DISPLAY.brightness = 1
    board.DISPLAY.show(self.text_area)

  def showMessage (self, msg):
    self.text_area.color = 0x00FFFF
    self.text_area.text = msg
    print(msg + '\n')

  def showError (self, msg):
    self.text_area.color = 0xFF0000
    self.text_area.text = msg
    print(msg)
  
  def report(self, data):
    try:
      # msg = "Internal: %.2f hPa\nAmbient: %.2f hPa\nDelta: %.2f hPa\nTemperature: %.2f F" % (data["internal"], data["ambient"], data["delta"], data["temp"])
      # if data['delta'] < (self.threshold * -1):
      #   self.showMessage(msg)
      # else:
      #   self.showError(msg)

      props = ("co2", "eco2", "temp", "hum", "aqi", "voc", "pm25")

      def isInList (prop):
        return props.count(prop[0]) > 0

      msg = '\n'.join(f'{k}={v}' for k,v in filter(isInList, data.items()))

      # text = '; '.join(f'{k}={v}' for k,v in data.items())
      # msg = "\n".join(wrap_text_to_lines(text, 28))

      self.showMessage(msg)
    except Exception as e:
      print('DisplayReporter error: ' + str(e))
