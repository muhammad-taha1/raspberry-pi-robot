import argparse
import sys
from time import sleep

from robotd.actors.supervisor import Supervisor
from robotd.config import DEFAULT_CONFIG_PATH, load
from robotd.hal.leds import GpioLed
from robotd.messages import SetLed


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


def run(config_path: str) -> int:
    """Start the actor tree, light the status LED, and run until interrupted."""
    cfg = load(config_path)
    with Supervisor(cfg) as robot:
        robot.status.tell(SetLed(True))
        print("robotd: running (Ctrl-C to stop)")
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
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

    return run(args.config)


if __name__ == "__main__":
    sys.exit(main())
