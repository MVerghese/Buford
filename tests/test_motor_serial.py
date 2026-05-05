#!/usr/bin/env python3
"""
Hardware integration script: exercise Gimbus motor over serial with velocity,
position, and torque commands.

Requires a flashed Gimbus driver and USB serial (see README). Not run by
default in pytest — invoke explicitly:

    uv run python tests/test_motor_serial.py --port /dev/ttyACM0

Or set MOTOR_SERIAL_PORT and omit --port.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Project src layout: drive_motors lives under src/
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from drive_motors.Motor_Communication import (  # noqa: E402
    DEFAULT_BAUDRATE,
    ControlType,
    DebugMessage,
    GimbusMotorSerial,
    Telemetry,
)

# Firmware heartbeat watchdog: send CMD at least every ~1000 ms
HEARTBEAT_INTERVAL_S = 0.5


def _drain_and_print_telemetry(motor: GimbusMotorSerial) -> None:
    """Read and print buffered ``TELEM:`` / ``DBG:`` lines (non-blocking via ``in_waiting``)."""
    ser = motor.serial_port
    while ser.in_waiting:
        msg = motor.read_message()
        if msg is None:
            break
        if isinstance(msg, Telemetry):
            print(
                f"  TELEM mode={msg.mode} target={msg.target:.4f} angle={msg.angle:.4f} "
                f"vel={msg.velocity:.4f} t_ms={msg.timestamp_ms}",
            )
        elif isinstance(msg, DebugMessage):
            print(f"  DBG {msg.text}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Test Gimbus motor: optional calibrate, then velocity, position, and torque over serial.",
    )
    p.add_argument(
        "--port",
        default=os.environ.get("MOTOR_SERIAL_PORT"),
        help="Serial device (default: env MOTOR_SERIAL_PORT)",
    )
    p.add_argument(
        "--baudrate",
        type=int,
        default=DEFAULT_BAUDRATE,
        help=f"Baud rate (default {DEFAULT_BAUDRATE})",
    )
    p.add_argument(
        "--velocity",
        type=float,
        default=2.0,
        help="Test velocity in rad/s (default 2.0)",
    )
    p.add_argument(
        "--velocity-duration",
        type=float,
        default=3.0,
        help="How long to run velocity test in seconds (default 3.0)",
    )
    p.add_argument(
        "--position",
        type=float,
        default=0.785398,
        help="Target position in rad for position test (default π/4)",
    )
    p.add_argument(
        "--position-hold",
        type=float,
        default=2.0,
        help="How long to hold position mode with heartbeats (default 2.0)",
    )
    p.add_argument(
        "--torque",
        type=float,
        default=0.2,
        help="Test torque as voltage (driver clamps to about ±1.2 V; default 0.2)",
    )
    p.add_argument(
        "--torque-duration",
        type=float,
        default=2.0,
        help="How long to run torque mode with heartbeats (default 2.0)",
    )
    p.add_argument(
        "--calibrate",
        action="store_true",
        help="Send CMD:R and wait before motion tests (custom firmware; off by default).",
    )
    p.add_argument(
        "--calibrate-wait",
        type=float,
        default=10.0,
        help="Seconds to sleep after CMD:R (default 10). Only used with --calibrate.",
    )
    return p.parse_args()


def _heartbeat_loop(
    motor: GimbusMotorSerial,
    control: ControlType,
    value: float,
    duration_s: float,
) -> None:
    end = time.monotonic() + duration_s
    while time.monotonic() < end:
        motor.send_command(control, value)
        _drain_and_print_telemetry(motor)
        time.sleep(HEARTBEAT_INTERVAL_S)
        _drain_and_print_telemetry(motor)


def main() -> int:
    args = _parse_args()
    if not args.port:
        print(
            "Error: serial port required. Pass --port /dev/ttyACM0 or set MOTOR_SERIAL_PORT.",
            file=sys.stderr,
        )
        return 2

    print(f"Opening {args.port} @ {args.baudrate} baud …")
    try:
        motor = GimbusMotorSerial(args.port, baudrate=args.baudrate, timeout=0.1)
    except OSError as e:
        print(f"Failed to open serial: {e}", file=sys.stderr)
        return 1

    try:
        if args.calibrate:
            print("--- Calibrate ---")
            motor.send_command(ControlType.CALIBRATE)
            print(f"  Waiting {args.calibrate_wait}s after CMD:R …")
            time.sleep(args.calibrate_wait)
            print("--- Calibrate done ---")

        print("--- Velocity test ---")
        print(f"  CMD:V:{args.velocity} for ~{args.velocity_duration}s (with heartbeat)")
        _heartbeat_loop(
            motor,
            ControlType.VELOCITY,
            args.velocity,
            args.velocity_duration,
        )

        # print("--- Position test ---")
        # print(f"  CMD:P:{args.position} for ~{args.position_hold}s (with heartbeat)")
        # _heartbeat_loop(
        #     motor,
        #     ControlType.POSITION,
        #     args.position,
        #     args.position_hold,
        # )

        # print("--- Torque test ---")
        # print(
        #     f"  CMD:T:{args.torque} for ~{args.torque_duration}s (with heartbeat)",
        # )
        # _heartbeat_loop(
        #     motor,
        #     ControlType.TORQUE,
        #     args.torque,
        #     args.torque_duration,
        # )

        print("--- Disable ---")
        motor.send_command(ControlType.DISABLE)
        print("Done.")
        return 0
    finally:
        motor.close()


if __name__ == "__main__":
    raise SystemExit(main())
