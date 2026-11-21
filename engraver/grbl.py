"""Creality CV-01 Pro over USB.

The board is an ESP32-S2 speaking GRBL 1.3a at 115200 on
/dev/cu.usbmodem1234561. The firmware calls the machine CV-01-Pro.
Raising DTR resets it and starts homing, so this module clears DTR
and RTS before the port is configured.

Vendor commands from the help line:
  $S   named settings, such as $Spindle/Type=LASER
  $L   which short $ number matches which name
  $+   the same settings in short form, including the CV-01 extras
  $E   error numbers in words

Travel is 170 mm in X and 200 mm in Y. Steps are 80/mm on X and
160/mm on Y. $30 is 1000, so S800 is 80%. Laser mode ($32) is on.
The spindle is a LASER and its PWM invert setting is On.

Jogs are $J=G91 and do not change absolute mode. A positive jog word
moves the reported machine position the other way: X10 takes MPos X
from 0 to -10, and X-10 brings it back.

A short mark has to use M3, which holds the power steady. M4 lowers
the power while the head is still speeding up, and a 2 mm line at 30%
left no mark. S800 at 150 mm/min over 5 mm did mark paper.

M5 stops the diode. On this machine that leaves the module fan running
and the red power light on. A controller reboot does turn both off, and
it also homes and shakes the head into the endstops. This module never
sends a soft reset and never raises DTR. The switch on the box is how
the module power goes off.
"""

import re
import time

import serial

PORT = "/dev/cu.usbmodem1234561"
BAUD = 115200

# Realtime bytes. They are not lined up with the other commands.
STATUS = b"?"
JOG_CANCEL = b"\x85"
FEED_HOLD = b"!"


class Link:
    def __init__(self, port=PORT, baud=BAUD):
        self.port = port
        self.baud = baud
        self.ser = None

    def open(self):
        ser = serial.Serial()
        ser.port = self.port
        ser.baudrate = self.baud
        ser.timeout = 0.2
        ser.write_timeout = 1
        ser.dsrdtr = False
        ser.rtscts = False
        # pyserial defaults these high. High DTR on open reboots the ESP32
        # and the reboot runs the homing cycle.
        ser.dtr = False
        ser.rts = False
        ser.open()
        ser.dtr = False
        ser.rts = False
        self.ser = ser
        return self

    def close(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.dtr = False
            self.ser.rts = False
            self.ser.close()
        self.ser = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    def write(self, data):
        self.ser.write(data)
        self.ser.flush()

    def read_for(self, seconds):
        deadline = time.monotonic() + seconds
        chunks = []
        while time.monotonic() < deadline:
            waiting = self.ser.in_waiting
            if waiting:
                chunks.append(self.ser.read(waiting))
            else:
                time.sleep(0.02)
        return b"".join(chunks).decode("utf-8", "replace")

    def lines(self, seconds):
        text = self.read_for(seconds)
        return [line.strip() for line in text.splitlines() if line.strip()]

    def stop_startup_motion(self):
        """Stop a homing run if opening the port rebooted the board."""
        self.write(JOG_CANCEL + FEED_HOLD)
        time.sleep(0.4)
        report = self.status()
        if "Hold" in report:
            self.write(b"~")
            time.sleep(0.3)
            report = self.status()
        if "Alarm" in report:
            self.command("$X")
            report = self.status()
        return report

    def status(self):
        """Where the machine is. '?' does not move or fire."""
        self.write(STATUS)
        seen = self.lines(0.4)
        for line in reversed(seen):
            if line.startswith("<") and line.endswith(">"):
                return line
        return seen[-1] if seen else ""

    def command(self, line, wait=2.0):
        """Send one line and collect replies until ok or error."""
        self.write((line.strip() + "\n").encode("ascii"))
        deadline = time.monotonic() + wait
        got = []
        while time.monotonic() < deadline:
            for reply in self.lines(0.12):
                if reply.startswith("<"):
                    continue
                got.append(reply)
                if reply == "ok" or reply.startswith("error:"):
                    return got
        return got

    def run(self, line, wait=2.0):
        """Send one line. Raise if the board does not answer ok."""
        got = self.command(line, wait)
        if not got or got[-1] != "ok":
            self.command("M5 S0")
            raise RuntimeError(f"{line} -> {got}")
        return got

    def wait_idle(self, timeout=10):
        deadline = time.monotonic() + timeout
        report = ""
        while time.monotonic() < deadline:
            report = self.status()
            if report.startswith("<Idle") or "Alarm" in report:
                return report
            time.sleep(0.05)
        return report


def connect(port=PORT):
    """Open the link. Stop startup motion if the open rebooted the board."""
    link = Link(port).open()
    boot = link.lines(0.6)
    if any(line.startswith("Grbl") or "tarx=" in line for line in boot):
        link.stop_startup_motion()
    return link


def machine_position(report):
    """Machine position in mm from an MPos status report."""
    found = re.search(r"MPos:([-\d.]+),([-\d.]+),([-\d.]+)", report)
    if not found:
        raise RuntimeError(f"no position in {report!r}")
    return tuple(float(part) for part in found.groups())


def named_settings(link):
    """The CV-01 named settings from $S, as a dict."""
    lines = link.command("$S", wait=3)
    if not lines or lines[-1] != "ok":
        raise RuntimeError(f"$S -> {lines}")
    settings = {}
    for line in lines:
        if line.startswith("$") and "=" in line:
            name, value = line[1:].split("=", 1)
            settings[name] = value
    return settings


def jog(link, x=0.0, y=0.0, feed=1000):
    """Relative move in millimetres. The laser stays off.

    feed is mm/min. 0x85 would cancel the jog. The sign in the command
    is the sign to send: positive X decreases the reported MPos.
    """
    line = f"$J=G91 X{x:.3f} Y{y:.3f} F{int(feed)}"
    link.run(line, wait=8)
    end = link.wait_idle()
    if "Alarm" in end:
        raise RuntimeError(end)
    return end


def laser_off(link):
    """Stop the diode and end the program.

    M5 S0 is beam off. M9 is coolant off. M2 is program end. The fan and
    the red module light stay on after this. Rebooting the board turns
    them off and also homes, so this function does not reset.
    """
    replies = []
    for line in ("M5 S0", "M9", "M2"):
        replies.extend(link.command(line, wait=2))
    return replies


def mark(link, length=5, feed=150, power=800):
    """Burn `length` mm toward +X at a constant S value, then return.

    M3 holds power for the whole move. G91 makes the length relative to
    the current point. The return is a rapid, which forces the beam off,
    and laser_off() still runs if a line fails.
    """
    try:
        for line in (
            "G21",
            "G90",
            f"M3 S{int(power)}",
            f"G91 G1 F{int(feed)} X{length:.3f} S{int(power)}",
            f"G91 G0 X{-length:.3f}",
            "G90",
        ):
            link.run(line, wait=8)
        end = link.wait_idle()
        if "Alarm" in end:
            raise RuntimeError(end)
        return end
    finally:
        laser_off(link)


def identify(port=PORT):
    """Open, read the firmware banner and the position, close."""
    notes = []
    with Link(port) as link:
        boot = link.lines(0.6)
        if any(line.startswith("Grbl") or "tarx=" in line for line in boot):
            notes.append("open reset the board; startup motion was stopped")
            notes.extend(boot)
            link.stop_startup_motion()
        identity = link.command("$I")
        report = link.status()
    return {"boot": notes, "identity": identity, "status": report}


if __name__ == "__main__":
    info = identify()
    for line in info["boot"]:
        print(line)
    for line in info["identity"]:
        print(line)
    print(info["status"])
