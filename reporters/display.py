# reporters/display.py
#
# Shows air quality readings on the ESP32-S3's built-in TFT, plus a persistent
# error indicator and an error log page.
#
# Screen structure:
#
#   root Group
#   ├── PageLayout
#   │   ├── page "mode0".."modeN": GridLayout of metrics   <- button cycles these
#   │   ├── page "log": list of reporter/sensor errors      <- ...and this one
#   │   └── page "message": big centered text, boot status  <- NOT in the cycle
#   └── indicator: a red "!" in the top-right corner, drawn above every page,
#                  visible only while at least one error is active

import time
import board
import terminalio
import displayio
from adafruit_display_text import bitmap_label, wrap_text_to_pixels
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_displayio_layout.layouts.page_layout import PageLayout

GREEN = 0x00FA9A
YELLOW = 0xFFA500
RED = 0xFF0000

# Same metric/page tables as before. See the earlier version for details on
# each option ("label", "fmt", "convert").
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

PAGES = (
  ("voc", "pm25", "co2"),
  ("temp", "hum"),
  ("voc", "nox"),
  ("pm1", "pm4", "pm10"),
)

# Page indexes inside the PageLayout, which follow the order we add them in:
# data pages first, then the log page, then the transient message page.
LOG_PAGE = len(PAGES)
# How many pages the button cycles through (data pages + log page). The
# message page is deliberately left out; it's only used for boot status.
NUM_MODES = len(PAGES) + 1

# The log page is drawn at scale 1 (smallest text) so more fits. Leave room on
# the right so wrapped text doesn't run under the "!" indicator.
LOG_MARGIN = 4
LOG_WRAP_WIDTH_RESERVED = 30
LOG_MAX_LINES = 12


def _label(text, scale):
  return bitmap_label.Label(terminalio.FONT, text=text, scale=scale)


def _age(ns):
  # Format a nanosecond duration as a short string like 45s, 12m or 3h.
  seconds = ns // 1_000_000_000
  if seconds < 60:
    return f"{seconds}s"
  if seconds < 3600:
    return f"{seconds // 60}m"
  return f"{seconds // 3600}h"


class DisplayReporter:

  def __init__(self, thresholds):
    self.thresholds = thresholds

    # code.py uses this name when it logs or clears errors for this reporter.
    self.name = "display"

    self.display = board.DISPLAY
    self.display.brightness = 0.6

    # Index of the page the button has selected (0..NUM_MODES-1).
    self.mode = 0

    self.cells = {key: [] for key in METRICS}

    # One entry per error source ("sensor", "influx", "display", ...):
    #   self.errors["influx"] = {"msg": "HTTP 401", "since": <ns>, "active": True}
    # Keyed by source, so the dict can never grow beyond a handful of entries
    # no matter how long an outage lasts.
    # "since" is when the state last changed: the failure start while active,
    # or the recovery time once active is False.
    self.errors = {}

    width, height = self.display.width, self.display.height

    self.pages = PageLayout(0, 0)

    # ---- data pages (indexes 0 .. len(PAGES)-1) ----
    for page_index, keys in enumerate(PAGES):
      grid = GridLayout(0, 0, width, height, grid_size=(len(keys), 2))
      for column, key in enumerate(keys):
        value_label = _label("000", 2)
        name_label = _label(METRICS[key]["label"], 1)
        grid.add_content(value_label, (column, 0), (1, 1), (0.5, 0.9))
        grid.add_content(name_label, (column, 1), (1, 1), (0.5, 0.1))
        self.cells[key].append((value_label, name_label))
      self.pages.add_content(grid, page_name=f"mode{page_index}")

    # ---- log page (index LOG_PAGE) ----
    # One multi-line label anchored to the top-left corner.
    self.log_label = _label("", 1)
    self.log_label.anchor_point = (0, 0)
    self.log_label.anchored_position = (LOG_MARGIN, LOG_MARGIN)
    self.pages.add_content(self.log_label, page_name="log")

    # ---- message page (index LOG_PAGE + 1) ----
    # Big centered text for boot status ("Sensor initialized"), same as before.
    self.message = _label("", 2)
    self.message.anchor_point = (0.5, 0.5)
    self.message.anchored_position = (width // 2, height // 2)
    self.message.color = GREEN
    self.pages.add_content(self.message, page_name="message")

    # ---- error indicator ----
    # A plain "!" label in the corner. It lives in the root group next to the
    # PageLayout (not inside it), so it's drawn on top of whichever page is
    # showing. A text label is cheap on RAM; swap it for a vectorio.Circle if
    # you want something fancier.
    self.indicator = _label("!", 2)
    self.indicator.color = RED
    self.indicator.anchor_point = (1, 0)               # anchor to its own top-right...
    self.indicator.anchored_position = (width - 4, 2)  # ...and put that near the corner
    self.indicator.hidden = True                       # shown only while errors are active

    self.root = displayio.Group()
    self.root.append(self.pages)
    self.root.append(self.indicator)
    self.display.root_group = self.root

    self._render_log()
    self.pages.show_page(page_name="message")

  # -------------------------------------------------------------------------
  # Boot/status messages (transient, full screen, not part of the error log)
  # -------------------------------------------------------------------------

  def showMessage(self, msg):
    """Show big centered status text. The next report() switches back to the
    selected page, same as before."""
    self.message.text = msg
    self.pages.show_page(page_name="message")
    print(msg)

  # -------------------------------------------------------------------------
  # Error tracking
  # -------------------------------------------------------------------------

  @property
  def has_errors(self):
    # True if any source is currently failing. code.py also uses this to
    # drive the NeoPixel.
    return any(err["active"] for err in self.errors.values())

  def logError(self, source, error):
    # Record that `source` is failing. Safe to call every loop while it
    # keeps failing; the original start time is kept.
    msg = str(error)
    print(source + " error: " + msg)

    existing = self.errors.get(source)
    if existing and existing["active"]:
      # Still failing: keep when it started, but show the latest message.
      existing["msg"] = msg
    else:
      # New failure (or a relapse after recovery): start the clock.
      self.errors[source] = {"msg": msg, "since": time.monotonic_ns(), "active": True}

    self._refresh_log()

  def clearError(self, source):
    # Record that `source` worked. A no-op unless it was failing. The entry
    # stays in the log as 'ok' so you can still see a blip that happened while
    # you weren't looking.
    err = self.errors.get(source)
    if err and err["active"]:
      err["active"] = False
      err["since"] = time.monotonic_ns()
      self._refresh_log()

  def _refresh_log(self):
    # Indicator on if anything is failing, off otherwise.
    self.indicator.hidden = not self.has_errors
    self._render_log()

  def _render_log(self):
    # Rebuild the log page text from self.errors.
    if not self.errors:
      self.log_label.color = GREEN
      self.log_label.text = "No errors"
      return

    now = time.monotonic_ns()
    wrap_width = self.display.width - LOG_MARGIN - LOG_WRAP_WIDTH_RESERVED
    lines = []

    for source, err in self.errors.items():
      age = _age(now - err["since"])
      if err["active"]:
        lines.append(f"! {source}: failing for {age}")
        # Wrap the (often long) message and indent it under the heading.
        for line in wrap_text_to_pixels(err["msg"], wrap_width, terminalio.FONT):
          lines.append("  " + line)
      else:
        lines.append(f"  {source}: ok for {age}")
        lines.append("  (last: " + err["msg"][:24] + ")")

    # Don't run off the bottom of the screen.
    self.log_label.text = "\n".join(lines[:LOG_MAX_LINES])
    # One color for the whole label: red while anything is failing.
    self.log_label.color = RED if self.has_errors else GREEN

  # -------------------------------------------------------------------------
  # Coloring
  # -------------------------------------------------------------------------

  def _color(self, key, value):
    t = self.thresholds
    color = GREEN
    if any(lo <= value < hi for lo, hi in t[key + "_caution"]):
      color = YELLOW
    if any(lo <= value < hi for lo, hi in t[key + "_danger"]):
      color = RED
    return color

  # -------------------------------------------------------------------------
  # Display modes
  # -------------------------------------------------------------------------

  def incrementMode(self):
    # Button handler: data pages..., then the log page, then back to the first.
    self.mode = (self.mode + 1) % NUM_MODES
    if self.mode == LOG_PAGE:
      self._render_log()  # refresh the "for 12m" ages before showing
    self.pages.show_page(page_index=self.mode)

  # -------------------------------------------------------------------------
  # Reporting
  # -------------------------------------------------------------------------

  def report(self, data):
    # Update every label from a fresh set of readings.
    #
    # Exceptions are NOT caught here anymore. code.py's report() wrapper catches
    # them and calls logError("display", e), so every reporter's failures end up
    # in the same place.
    for key, spec in METRICS.items():
      value = data[key]
      if "convert" in spec:
        value = spec["convert"](value)

      color = self._color(key, value)
      text = spec.get("fmt", "%s") % value

      for value_label, name_label in self.cells[key]:
        value_label.text = text
        value_label.color = color
        name_label.color = color

    # Return to the page the button selected (also dismisses a boot message).
    self.pages.show_page(page_index=self.mode)

    # If you're sitting on the log page, keep its ages current.
    if self.mode == LOG_PAGE:
      self._render_log()