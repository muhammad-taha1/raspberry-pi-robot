import argparse
import sys
from time import sleep

from robotd.config import DEFAULT_CONFIG_PATH, load
from robotd.hal.leds import GpioLed


def check(config_path: str) -> int:
    """Exercise every registered real device once and report pass/fail."""
    cfg = load(config_path)

    print("led ... ", end="", flush=True)
    led = GpioLed(cfg.pin("led"))
    try:
        led.on()
        sleep(0.3)
        led.off()
        sleep(0.3)
        led.on()
        sleep(0.3)
        led.off()
        print("ok")
    finally:
        led.close()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="robotd")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exercise every registered device once and exit",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    args = parser.parse_args()

    if args.check:
        return check(args.config)

    print("robotd: no actors yet (M0) — try --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
