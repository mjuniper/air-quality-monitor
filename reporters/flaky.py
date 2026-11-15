# reporters/flaky.py
#
# A reporter that fails a few times in a row to test error handling.

class FlakyReporter:
  name = "flaky"
  def __init__(self):
    self.n = 0
  def report(self, data):
    self.n += 1
    if 2 <= self.n <= 4:
      raise RuntimeError("test failure " + str(self.n))