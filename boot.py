# boot.py
#
# Runs once at power-up or hard reset (not on a code reload).
#
# Normal boot: hide the CIRCUITPY USB drive. The board is edited over Wi-Fi (web
# workflow), which can only write to the filesystem while a computer isn't
# mounting it over USB.
#
# Recovery boot: tap RESET, then press and hold the button while the NeoPixel is
# blue (about 3 seconds). The NeoPixel turns green and the USB drive stays on.
# (Holding it through the reset works too.)
#
# The button is button_pin in settings.toml (default D1). D1 and D2 read high when
# pressed; D0 is the BOOT button, which reads low when pressed. Avoid holding D0
# *through* a reset: GPIO0 held at reset drops the chip into its ROM bootloader.
#
# If anything goes wrong checking the button (say a typo in button_pin), the USB
# drive is left enabled so a bad setting can't lock you out.

import os
import time
import board
import digitalio
import neopixel
import storage

WINDOW_SECONDS = 3

try:
  pin_name = os.getenv("button_pin", "D1")
  active_low = pin_name == "D0"

  pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
  button = digitalio.DigitalInOut(getattr(board, pin_name))
  button.switch_to_input(pull=digitalio.Pull.UP if active_low else digitalio.Pull.DOWN)

  pixel[0] = (0, 0, 255)  # blue: press and hold the button now to keep USB storage
  held = False
  deadline = time.monotonic() + WINDOW_SECONDS
  while time.monotonic() < deadline:
    if button.value != active_low:  # pressed
      held = True
      break
    time.sleep(0.02)
  button.deinit()

  if held:
    pixel[0] = (0, 255, 0)  # green: USB mass storage stays enabled
    time.sleep(1)
  else:
    storage.disable_usb_drive()
    pixel[0] = (0, 0, 0)
except Exception as e:
  print("boot.py: " + type(e).__name__ + ": " + str(e) + " (leaving USB drive enabled)")
