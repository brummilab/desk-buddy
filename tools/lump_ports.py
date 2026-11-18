"""Finding Lump on USB, and pausing the bridge while another tool needs the port. Shared by the
bridge (tools/buddy_bridge.py), tools/wifi_setup.py and tools/flash.ps1, on macOS and Windows.

    python tools/lump_ports.py          # print the ports Lump could be on, best first (flash.ps1 uses this)
    python tools/lump_ports.py -v       # ...and every serial port with its USB ids, to check the filter

macOS: the board's CH343 USB-serial chip shows up as /dev/cu.usbmodem*, and nothing else does.
Windows: every serial port is a COMx (Bluetooth, docks, modems...), so only ports with WCH's CH343
family USB ids count. "serial_port" in ~/.desk-buddy/config.json (or DESKBUDDY_PORT) pins one port.
"""
import contextlib, glob, json, os, subprocess, sys, time

IS_WIN = sys.platform == "win32"
HOME = os.environ.get("DESKBUDDY_HOME") or os.path.expanduser("~/.desk-buddy")
CONFIG = os.path.join(HOME, "config.json")

# WCH (Nanjing Qinheng) CH343 / CH9102 family. Not the older CH340 (0x7523): that one sits on lots of
# other boards (Arduino clones, 3D printers), and the bridge would end up talking to them.
WCH_VID = 0x1A86
CH343_PIDS = {0x55D2, 0x55D3, 0x55D4, 0x55D5, 0x55D8}

# Windows: the bridge runs as this scheduled task (tools/install_bridge.ps1)
TASK = "DeskBuddyBridge"
# macOS: ...and as this launchd agent (tools/install_bridge.sh)
LABEL = "com.deskbuddy.bridge"
PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")


def pinned():
    """A port set by hand: DESKBUDDY_PORT, else "serial_port" in config.json. None if neither."""
    if os.environ.get("DESKBUDDY_PORT"):
        return os.environ["DESKBUDDY_PORT"]
    try:
        with open(CONFIG) as f:
            return json.load(f).get("serial_port") or None
    except Exception:
        return None


def is_lump(port):
    """port: a serial.tools.list_ports entry. Does it look like the board's USB-serial chip?"""
    return port.vid == WCH_VID and port.pid in CH343_PIDS


def usb_ports():
    """Serial ports Lump could be on, sorted. Doesn't include a pinned port (see pinned())."""
    if not IS_WIN:
        return sorted(glob.glob("/dev/cu.usbmodem*"))
    from serial.tools import list_ports
    return sorted((p.device for p in list_ports.comports() if is_lump(p)), key=_com_order)


def _com_order(name):
    digits = "".join(c for c in name if c.isdigit())
    return (int(digits) if digits else 0, name)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


@contextlib.contextmanager
def bridge_paused():
    """The bridge holds the USB port (on Windows, exclusively): stop it while the board is ours,
    and start it again afterwards, whatever happens. Does nothing if the bridge isn't installed."""
    if IS_WIN:
        installed = _run(["schtasks", "/Query", "/TN", TASK]).returncode == 0
        if installed:
            _run(["schtasks", "/End", "/TN", TASK])
    else:
        installed = os.path.exists(PLIST)
        if installed:
            _run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"])
    if installed:
        time.sleep(1)                          # let it let go of the port
    try:
        yield
    finally:
        if installed:
            if IS_WIN:
                _run(["schtasks", "/Run", "/TN", TASK])
            else:
                _run(["launchctl", "bootstrap", f"gui/{os.getuid()}", PLIST])


def main():
    if "-v" in sys.argv:
        from serial.tools import list_ports
        for p in list_ports.comports():
            ids = f"{p.vid:04X}:{p.pid:04X}" if p.vid is not None else "no USB ids"
            mark = "  <- Lump?" if IS_WIN and is_lump(p) else ""
            print(f"{p.device:12} {ids:10} {p.description}{mark}", file=sys.stderr)
    ports = ([pinned()] if pinned() else []) + usb_ports()
    for p in ports:
        print(p)
    return 0 if ports else 1


if __name__ == "__main__":
    sys.exit(main())
