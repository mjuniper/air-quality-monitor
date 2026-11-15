# reporters/display.py
#
# Shows air quality readings on the ESP32-S3's built-in TFT.
#
# How the screen is organized:
#
#   PageLayout (root of the display)
#   ├── page "mode0": GridLayout  -> voc, pm25, co2
#   ├── page "mode1": GridLayout  -> temp, hum
#   ├── page "mode2": GridLayout  -> voc, nox
#   ├── page "mode3": GridLayout  -> pm1, pm4, pm10
#   └── page "message": one centered Label, used for status and error text
#
# PageLayout shows exactly one page at a time, so switching display modes is
# just "show a different page". Each page's GridLayout has one column per
# metric and two rows: the big number on top and the name underneath.
#
# Docs:
#   https://learn.adafruit.com/circuitpython-display-support-using-displayio/introduction
#   https://learn.adafruit.com/circuitpython-display_text-library/overview
#   https://docs.circuitpython.org/projects/displayio_layout/en/latest/

import board
import terminalio
from adafruit_display_text import bitmap_label, wrap_text_to_pixels
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_displayio_layout.layouts.page_layout import PageLayout

# Status colors as 24-bit RGB hex values (0xRRGGBB).
GREEN = 0x00FA9A   # reading is fine
YELLOW = 0xFFA500  # caution range
RED = 0xFF0000     # danger range (also used for error messages)

# ---------------------------------------------------------------------------
# METRICS: everything that differs from one measurement to the next lives here.
#
# The key (e.g. "pm25") has to match two other things:
#   1. the key in the `data` dict that code.py passes to report()
#   2. the prefix of the threshold names in secrets['thresholds'],
#      i.e. "pm25_caution" and "pm25_danger"
#
# Per-metric options:
#   "label"   : the name shown under the number (required)
#   "fmt"     : a printf-style format for the number. Defaults to "%s", which
#               just uses str(value). Use "%.0f" or "%.1f" to control decimals.
#   "convert" : optional function applied to the raw value BEFORE coloring and
#               display. Thresholds are compared against the converted value,
#               so the temp thresholds in secrets must be in Fahrenheit.
# ---------------------------------------------------------------------------
METRICS = {
  "pm1":  {"label": "PM 1"},
  "pm25": {"label": "PM 2.5"},
  "pm4":  {"label": "PM 4"},
  "pm10": {"label": "PM 10"},
  "voc":  {"label": "VOC"},
  "nox":  {"label": "NOX"},
  "co2":  {"label": "CO2", "fmt": "%.0f"},
  "temp": {"label": "TEMP", "fmt": "%.1f", "convert": lambda c: c * 1.8 + 32},  # C -> F
  "hum":  {"label": "HUM", "fmt": "%.1f"},
}

# ---------------------------------------------------------------------------
# PAGES: which metrics appear on each display mode, left to right.
#
# The button in code.py cycles through these in order. To add, remove or
# reorder a screen, just edit this tuple. The same metric can appear on more
# than one page (voc is on two). Keep to 3 or fewer columns per page: at
# scale=3 each digit is 18px wide, and a 240px display gets crowded fast.
# ---------------------------------------------------------------------------
PAGES = (
  ("voc", "pm25", "co2"),   # mode 0
  ("temp", "hum"),          # mode 1
  ("voc", "nox"),           # mode 2
  ("pm1", "pm4", "pm10"),   # mode 3
)


def _label(text, scale):
  # Small helper so we don't repeat the long Label constructor everywhere.

  # bitmap_label.Label renders text into a bitmap. It uses less RAM and is
  # faster to update than the plain label.Label class, which matters on a
  # microcontroller. `scale` is an integer multiplier on the font size.
  
  return bitmap_label.Label(terminalio.FONT, text=text, scale=scale)


class DisplayReporter:

  def __init__(self, params):
    # Threshold ranges from secrets.py. Each looks like:
    #   "pm25_caution": ((12, 35), (35, 55)), ...   i.e. ((min, max), (min, max))
    self.thresholds = params["thresholds"]

    # board.DISPLAY is created by CircuitPython at boot for boards with a
    # built-in screen. Keep a short reference to it.
    self.display = board.DISPLAY
    self.display.brightness = 0.6

    # Index into PAGES of the data page currently selected by the button.
    # Tracked separately from what's on screen, because the message page can
    # temporarily cover the data page and we need to know what to come back to.
    self.mode = 0

    # Lookup table of every on-screen label, grouped by metric:
    #   self.cells["voc"] -> [(value_label, name_label), (value_label, name_label)]
    # "voc" has two entries because it's on two pages. When a new voc reading
    # arrives we update both, so whichever page is showing is always current.
    self.cells = {key: [] for key in METRICS}

    width, height = self.display.width, self.display.height

    # PageLayout holds several "pages" (any displayio Group works as one) and
    # shows only one at a time. The (0, 0) is its x, y position on screen.
    self.pages = PageLayout(0, 0)

    # Build one GridLayout page per entry in PAGES.
    for page_index, keys in enumerate(PAGES):

      # A grid that fills the whole screen. grid_size is (columns, rows):
      # one column per metric, and two rows (number on top, name below).
      # The grid divides the screen evenly, which replaces all the hand-tuned
      # x/y coordinates and padding values from the old version.
      grid = GridLayout(0, 0, width, height, grid_size=(len(keys), 2))

      for column, key in enumerate(keys):
        # The big number. "000" is a placeholder until the first reading;
        # the real text is set in report().
        value_label = _label("000", 2)

        # The smaller metric name, taken from the METRICS table.
        name_label = _label(METRICS[key]["label"], 1)

        # add_content(item, grid_position, cell_size, cell_anchor_point)
        #   grid_position    : (column, row) of the top-left cell it occupies
        #   cell_size        : (1, 1) means it spans a single cell
        #   cell_anchor_point: (0.5, 0.5) centers it in the cell. (0, 0) would
        #                      be top-left and (1, 1) bottom-right.
        grid.add_content(value_label, (column, 0), (1, 1), (0.5, 0.9))
        grid.add_content(name_label, (column, 1), (1, 1), (0.5, 0.1))

        # Remember the pair so report() can find it by metric key later.
        self.cells[key].append((value_label, name_label))

      # Register the finished grid as a page. The name lets us jump to it
      # with show_page(page_name=...), though we mostly use the index.
      self.pages.add_content(grid, page_name=f"mode{page_index}")

    # One extra page after the data pages: a single label for status and error
    # text. Because it is added last, its page index is len(PAGES), so it
    # never collides with the data page indexes 0..len(PAGES)-1.
    self.message = _label("", 2)
    # anchor_point says which part of the label the position refers to.
    # (0.5, 0.5) is its center, so the text is centered on the screen.
    self.message.anchor_point = (0.5, 0.5)
    self.message.anchored_position = (width // 2, height // 2)
    self.pages.add_content(self.message, page_name="message")

    # Make the PageLayout the root of the display (replaces the older
    # display.show(...) call). Start on the message page so boot messages show.
    self.display.root_group = self.pages
    self.pages.show_page(page_name="message")

  # -------------------------------------------------------------------------
  # Messages and errors
  # -------------------------------------------------------------------------

  def _show_message(self, msg, color):
    # Display centered, wrapped text on the message page.
    # Break the text into lines no wider than half the screen so it wraps
    # instead of running off the edge. wrap_text_to_pixels returns a list.
    lines = wrap_text_to_pixels(msg, self.display.width // 2, terminalio.FONT)

    self.message.color = color
    self.message.text = "\n".join(lines)

    # Switch the screen to the message page. It stays there until report()
    # or incrementMode() switches back to a data page.
    self.pages.show_page(page_name="message")

    # Also print to the serial console so you can see it over USB.
    print(msg + "\n")

  def showMessage(self, msg):
    # Show a normal status message in green.
    self._show_message(msg, GREEN)
    print(msg + "\n")

  def showError(self, msg):
    # Show an error message in red.
    self._show_message(msg, RED)
    print(msg + "\n")

  # -------------------------------------------------------------------------
  # Coloring
  # -------------------------------------------------------------------------

  def _color(self, key, value):
    # Return GREEN, YELLOW or RED for a reading, using the secrets thresholds.
    t = self.thresholds

    # Start from "all good", then escalate. Danger is checked last so it wins
    # if a value happens to fall inside both a caution and a danger range.
    color = GREEN

    # Ranges are half-open: a value matches if lo <= value < hi.
    # any(...) is True if the value falls inside at least one range.
    # (The old version used `range` as a variable name, which shadowed the
    # Python builtin of the same name. Unpacking into lo/hi avoids that.)
    if any(lo <= value < hi for lo, hi in t[key + "_caution"]):
      color = YELLOW
    if any(lo <= value < hi for lo, hi in t[key + "_danger"]):
      color = RED

    return color

  # -------------------------------------------------------------------------
  # Display modes
  # -------------------------------------------------------------------------

  def incrementMode(self):
    # Advance to the next data page, wrapping back to the first.
    # code.py calls this when the mode button is pressed. It also brings the
    # screen back from the message page if an error or status was showing.

    # The modulo operator wraps us back to 0 after the last page.
    self.mode = (self.mode + 1) % len(PAGES)
    self.pages.show_page(page_index=self.mode)

  # -------------------------------------------------------------------------
  # Reporting
  # -------------------------------------------------------------------------

  def report(self, data):
    # Update every label from a fresh set of readings.

    # `data` is the dict built in code.py, with keys matching METRICS.
    try:
      for key, spec in METRICS.items():
        value = data[key]

        # Apply a unit conversion if this metric has one (temp: C -> F).
        # We convert first so colors and text both use the converted number.
        if "convert" in spec:
          value = spec["convert"](value)

        color = self._color(key, value)

        # Format the number. spec.get("fmt", "%s") falls back to "%s" when no
        # format is given, which is the same as str(value).
        text = spec.get("fmt", "%s") % value

        # Update every on-screen copy of this metric (one per page it's on).
        # Color both the number and its name so the whole cell reads as one
        # status at a glance.
        for value_label, name_label in self.cells[key]:
          value_label.text = text
          value_label.color = color
          name_label.color = color

      # Fresh data is in, so switch to the selected data page. This also
      # clears any old error message that was covering the screen.
      self.pages.show_page(page_index=self.mode)

    except Exception as e:
      # Never let a display problem take down the sensor loop in code.py.
      print("DisplayReporter error: " + str(e))