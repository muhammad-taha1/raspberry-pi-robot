import sys
from time import sleep

from robotd.actors.supervisor import Supervisor
from robotd.config import DEFAULT_CONFIG_PATH, load
from robotd.web import COMMAND_PORT, serve


def main() -> int:
    cfg = load(DEFAULT_CONFIG_PATH)
    with Supervisor(cfg) as robot:
        server = serve(robot.commands, robot.brain)
        print(f"robotd: running on :{COMMAND_PORT} (Ctrl-C to stop)")
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
