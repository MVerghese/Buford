"""Serial client for the MotorGo Gimbus driver command protocol.

Protocol: https://github.com/Every-Flavor-Robotics/motorgo-gimbus-driver
USB CDC at 115200 baud; lines are newline-terminated. Send a valid CMD at
least every 1000 ms or the driver disables the motor (heartbeat watchdog).

Incoming lines (driver → host) are documented there:

- ``TELEM:<mode>:<target>:<angle>:<velocity>:<timestamp_ms>`` — telemetry at 10 Hz
- ``DBG:...`` — debug text (informational)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import serial

DEFAULT_BAUDRATE = 115200


class ControlType(Enum):
    """Jetson to driver command kinds (CMD:*)."""

    VELOCITY = "V"  # rad/s (device clamps to +/-100)
    POSITION = "P"  # radians
    TORQUE = "T"  # voltage (device clamps to +/-1.2 V)
    DISABLE = "O"  # CMD:O: stop and disable; no value
    CALIBRATE = "R"  # CMD:R: calibrate the motor


@dataclass(frozen=True)
class Telemetry:
    """One ``TELEM:`` line from the driver (see README telemetry table)."""

    mode: str  # V velocity, P position, T torque, D disabled, E error
    target: float
    angle: float
    velocity: float
    timestamp_ms: int


@dataclass(frozen=True)
class DebugMessage:
    """One ``DBG:`` line; ``text`` is the payload after the ``DBG:`` prefix."""

    text: str


def parse_driver_line(line: str) -> Telemetry | DebugMessage | None:
    """Parse a single driver line.

    Returns ``Telemetry`` for ``TELEM:``, ``DebugMessage`` for ``DBG:``,
    or ``None`` for empty lines or lines that are not those prefixes.
    Raises ``ValueError`` if a ``TELEM:`` line has the wrong shape or fields.
    """
    s = line.strip()
    if not s:
        return None
    if s.startswith("TELEM:"):
        parts = s.split(":")
        if len(parts) != 6:
            msg = f"TELEM line must have 6 colon-separated fields, got {len(parts)}: {s!r}"
            raise ValueError(msg)
        _prefix, mode, t_s, a_s, v_s, ts_s = parts
        if len(mode) != 1:
            msg = f"TELEM mode must be a single character, got {mode!r}"
            raise ValueError(msg)
        return Telemetry(
            mode=mode,
            target=float(t_s),
            angle=float(a_s),
            velocity=float(v_s),
            timestamp_ms=int(ts_s),
        )
    if s.startswith("DBG:"):
        return DebugMessage(text=s[4:])
    return None


class GimbusMotorSerial:
    """Send motor commands to Gimbus firmware over a serial port."""

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float | None = None,
    ) -> None:
        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

    @property
    def serial_port(self) -> serial.Serial:
        return self._serial

    def close(self) -> None:
        self._serial.close()

    def __enter__(self) -> GimbusMotorSerial:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def send_command(self, control: ControlType, value: float | None = None) -> None:
        """Send one newline-terminated command.

        ControlType.DISABLE sends CMD:O and ignores value.
        Other modes require value and send CMD:<V|P|T>:<float>.
        """
        if control is ControlType.DISABLE:
            line = "CMD:O"
        elif control is ControlType.CALIBRATE:
            line = "CMD:R"
        else:
            if value is None:
                msg = f"{control.name} requires a numeric value"
                raise TypeError(msg)
            line = f"CMD:{control.value}:{value}"
        self._serial.write((line + "\n").encode("ascii"))
        self._serial.flush()

    def read_line(self) -> str | None:
        """Read one newline-terminated line from the port (decoded, stripped).

        Returns ``None`` on timeout or empty read (depends on pyserial timeout).
        """
        raw = self._serial.readline()
        if not raw:
            return None
        return raw.decode("ascii", errors="replace").strip()

    def read_message(self) -> Telemetry | DebugMessage | None:
        """Read one line and parse ``TELEM:`` / ``DBG:`` per the driver README.

        Returns ``None`` if no data (timeout), blank line, or a non-protocol line.
        Raises ``ValueError`` for malformed ``TELEM:`` lines.
        """
        text = self.read_line()
        if text is None:
            return None
        return parse_driver_line(text)
