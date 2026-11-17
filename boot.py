import storage
import board
import digitalio
import neopixel
import time

# Initialize the built-in NeoPixel
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.2

# D1 is pulled LOW by default on this board and goes HIGH when pressed
button = digitalio.DigitalInOut(board.D1)
button.pull = digitalio.Pull.DOWN

if not button.value:
    # Normal boot (D1 NOT pressed): Disable USB mass storage for web workflow
    storage.disable_usb_drive()
    pixel[0] = (0, 0, 255)  # Blue
else:
    # Recovery boot (D1 HELD): Keep USB mass storage enabled
    pixel[0] = (0, 255, 0)  # Green

# Pause so i have time to see the color and release the button
time.sleep(2)