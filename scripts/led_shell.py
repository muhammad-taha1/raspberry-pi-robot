import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gpiozero import LED

from robotd.config import load

cfg = load()
led = LED(cfg.pin("led"))

print("LED test shell")
print("Commands: on, off, status, quit")

try:
    while True:
        command = input("> ").strip().lower()

        if command == "on":
            led.on()
            print("LED: ON")

        elif command == "off":
            led.off()
            print("LED: OFF")

        elif command == "status":
            print(f"LED: {'ON' if led.is_lit else 'OFF'}")

        elif command in ("quit", "exit", "q"):
            break

        else:
            print("Unknown command. Use: on, off, status, quit")

finally:
    led.off()
    led.close()
    print("LED: OFF")
    print("Exiting.")
