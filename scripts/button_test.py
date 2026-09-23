"""Print press/release events from the push-to-talk button, straight off gpiozero.

Proves the wiring and the pull-up before HearingActor is trusted with it.
"""

from __future__ import annotations

from datetime import datetime
from time import sleep

from gpiozero import Button

from robotd.config import load

cfg = load()
button = Button(cfg.pin("button"), bounce_time=0.05)


def log(event: str) -> None:
    print(f"{datetime.now().isoformat(timespec='milliseconds')}  {event}")


button.when_pressed = lambda: log("pressed")
button.when_released = lambda: log("released")

print(f"Watching GPIO {cfg.pin('button')} — press the button (Ctrl-C to stop)")
try:
    while True:
        sleep(1)
except KeyboardInterrupt:
    pass
finally:
    button.close()
    print("Test complete.")
