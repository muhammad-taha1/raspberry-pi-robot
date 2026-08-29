import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gpiozero import OutputDevice
from time import sleep

from robotd.config import load

cfg = load()

# L298N inputs
IN1 = OutputDevice(cfg.pin("motor_in1"), initial_value=False)
IN2 = OutputDevice(cfg.pin("motor_in2"), initial_value=False)

IN3 = OutputDevice(cfg.pin("motor_in3"), initial_value=False)
IN4 = OutputDevice(cfg.pin("motor_in4"), initial_value=False)


def stop():
    IN1.off()
    IN2.off()
    IN3.off()
    IN4.off()


def left_forward():
    IN1.on()
    IN2.off()


def left_reverse():
    IN1.off()
    IN2.on()


def right_forward():
    IN3.on()
    IN4.off()


def right_reverse():
    IN3.off()
    IN4.on()


try:
    print("LEFT motor forward")
    left_forward()
    sleep(2)
    stop()
    sleep(1)

    print("LEFT motor reverse")
    left_reverse()
    sleep(2)
    stop()
    sleep(1)

    print("RIGHT motor forward")
    right_forward()
    sleep(2)
    stop()
    sleep(1)

    print("RIGHT motor reverse")
    right_reverse()
    sleep(2)
    stop()

finally:
    # Always stop the motors if the program exits/errors.
    stop()
    IN1.close()
    IN2.close()
    IN3.close()
    IN4.close()

print("Test complete.")
