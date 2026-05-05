# Buford

Codebase for Buford, an open-source home robot.

## Motor serial test (hardware)

The script `tests/test_motor_serial.py` talks to a [MotorGo Gimbus](https://github.com/Every-Flavor-Robotics/motorgo-gimbus-driver) driver over USB serial: it runs a short **velocity** segment, then **position**, then **torque** (voltage command), then **disable**. Commands are repeated on a heartbeat so the firmware watchdog (1 s) does not cut power. Buffered **TELEM** / **DBG** lines are printed during each phase.

**Requirements:** Gimbus firmware flashed, motor connected, and the correct device path (often `/dev/ttyACM0` on Linux).

From the repo root:

```bash
uv run python tests/test_motor_serial.py --port /dev/ttyACM0
```

Or set the port once:

```bash
export MOTOR_SERIAL_PORT=/dev/ttyACM0
uv run python tests/test_motor_serial.py
```

Optional flags: `--baudrate` (default `115200`), `--velocity`, `--velocity-duration`, `--position`, `--position-hold`, `--torque`, `--torque-duration`, `--calibrate` (sends `CMD:R` then waits; for custom firmware), `--calibrate-wait` (seconds after `CMD:R`, default `10`). Use `--help` for details.

**Note:** This is an integration script, not part of the default unit test suite (`pytest` does not need hardware). Run it only when the board is connected and it is safe for the mechanism to move.
