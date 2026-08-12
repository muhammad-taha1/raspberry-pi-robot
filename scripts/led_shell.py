from gpiozero import LED

LED_PIN = 17

led = LED(LED_PIN)

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