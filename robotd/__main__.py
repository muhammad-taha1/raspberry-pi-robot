import argparse
import sys
from time import sleep

from robotd.actors.supervisor import Supervisor
from robotd.config import DEFAULT_CONFIG_PATH, load
from robotd.web import COMMAND_PORT, serve


def run(config_path: str) -> int:
    """Start the actor tree and the command endpoint; run until interrupted."""
    cfg = load(config_path)
    with Supervisor(cfg) as robot:
        server = serve(robot.commands)
        print(f"robotd: running, POST /command on :{COMMAND_PORT} (Ctrl-C to stop)")
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="robotd")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    args = parser.parse_args()

    return run(args.config)


if __name__ == "__main__":
    sys.exit(main())
