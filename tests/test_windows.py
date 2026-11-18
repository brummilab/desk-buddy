"""Tests for the Windows side of the bridge: finding the board by USB ids, sounds through winsound,
the status line and hooks for Windows. They run anywhere (Windows is faked with mocks):
    ~/.desk-buddy/venv/bin/python -m unittest discover -s tests -v
"""
import array, importlib.util, io, json, os, sys, tempfile, types, unittest, wave
from types import SimpleNamespace
from unittest import mock

HOME = os.environ.get("DESKBUDDY_HOME") or tempfile.mkdtemp(prefix="deskbuddy-test-")
os.environ["DESKBUDDY_HOME"] = HOME
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")
sys.path.insert(0, TOOLS)


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bridge = sys.modules.get("buddy_bridge") or load("buddy_bridge", "buddy_bridge.py")
import lump_ports
statusline = load("statusline", "statusline.py")
install_hooks = load("install_hooks", "install_hooks.py")


def port(device, vid=None, pid=None, description=""):
    return SimpleNamespace(device=device, vid=vid, pid=pid, description=description)


class FindingLump(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DESKBUDDY_PORT", None)
        self.addCleanup(lambda: os.path.exists(lump_ports.CONFIG) and os.remove(lump_ports.CONFIG))

    def ports(self, *found):
        from serial.tools import list_ports
        return mock.patch.multiple(lump_ports, IS_WIN=True), mock.patch.object(list_ports, "comports", lambda: list(found))

    def test_only_the_ch343_counts_on_windows(self):
        a, b = self.ports(port("COM3", description="Bluetooth link"),
                          port("COM12", 0x1A86, 0x55D3, "USB-Enhanced-SERIAL CH343"),
                          port("COM4", 0x1A86, 0x7523, "CH340 (a 3D printer)"),
                          port("COM9", 0x1A86, 0x55D4),
                          port("COM5", 0x0403, 0x6001, "FTDI"))
        with a, b:
            self.assertEqual(lump_ports.usb_ports(), ["COM9", "COM12"])    # by number, not as text

    def test_mac_still_uses_usbmodem(self):
        with mock.patch.object(lump_ports, "IS_WIN", False), \
             mock.patch.object(lump_ports.glob, "glob", lambda pat: ["/dev/cu.usbmodem2", "/dev/cu.usbmodem1"]) as g:
            self.assertEqual(lump_ports.usb_ports(), ["/dev/cu.usbmodem1", "/dev/cu.usbmodem2"])

    def test_a_port_can_be_pinned_in_config_or_env(self):
        self.assertIsNone(lump_ports.pinned())
        with open(lump_ports.CONFIG, "w") as f: json.dump({"serial_port": "COM7"}, f)
        self.assertEqual(lump_ports.pinned(), "COM7")
        with mock.patch.dict(os.environ, {"DESKBUDDY_PORT": "COM8"}):
            self.assertEqual(lump_ports.pinned(), "COM8")

    def test_bridge_uses_the_pinned_port_only(self):
        with open(lump_ports.CONFIG, "w") as f: json.dump({"serial_port": "COM7", "lump_token": "abc"}, f)
        d = bridge.Device.__new__(bridge.Device); d._last_err = {}
        self.assertEqual(d._targets(), ["COM7"])

    def test_pausing_the_bridge_ends_and_restarts_the_task(self):
        calls = []
        def run(cmd):
            calls.append(cmd[:2]); return SimpleNamespace(returncode=0)
        with mock.patch.object(lump_ports, "IS_WIN", True), mock.patch.object(lump_ports, "_run", run), \
             mock.patch.object(lump_ports.time, "sleep"):
            with self.assertRaises(SystemExit):
                with lump_ports.bridge_paused():
                    raise SystemExit("board didn't answer")
        self.assertEqual(calls, [["schtasks", "/Query"], ["schtasks", "/End"], ["schtasks", "/Run"]])

    def test_no_task_means_nothing_to_pause(self):
        calls = []
        def run(cmd):
            calls.append(cmd[:2]); return SimpleNamespace(returncode=1)
        with mock.patch.object(lump_ports, "IS_WIN", True), mock.patch.object(lump_ports, "_run", run):
            with lump_ports.bridge_paused(): pass
        self.assertEqual(calls, [["schtasks", "/Query"]])


class WindowsPaths(unittest.TestCase):
    def test_work_account_from_a_windows_transcript_path(self):
        self.assertEqual(bridge.account_of_config(r"C:\Users\me\.claude-work\projects\x\abc.jsonl"), "work")
        self.assertEqual(bridge.account_of_config(r"C:\Users\me\.claude\projects\x\abc.jsonl"), "personal")

    def test_no_focus_thread_on_windows(self):
        with mock.patch.object(bridge, "IS_WIN", True), mock.patch.object(bridge.threading, "Thread") as t:
            f = bridge.Focus()
        t.assert_not_called()
        self.assertFalse(f.front)
        self.assertIsNone(f.code_session)

    def test_slack_never_in_front_on_windows(self):
        with mock.patch.object(bridge, "IS_WIN", True), mock.patch.object(bridge.subprocess, "run") as run:
            self.assertFalse(bridge.SlackWatch.slack_in_front())
        run.assert_not_called()

    def test_second_bridge_cant_share_the_port_on_windows(self):
        self.assertEqual(bridge.Server.allow_reuse_address, not bridge.IS_WIN)


def write_wav(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(array.array("h", samples).tobytes())


def read_wav(path):
    with wave.open(path) as w:
        return list(array.array("h", w.readframes(w.getnframes())))


class WindowsSounds(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.wav = os.path.join(self.dir, "tap_shock.wav")
        write_wav(self.wav, [1000, -1000, 30000, -30000, 0])

    def test_full_volume_plays_the_original(self):
        self.assertEqual(bridge.scaled_wav(self.wav, 1.0), self.wav)

    def test_quieter_copy_is_made_once(self):
        out = bridge.scaled_wav(self.wav, 0.4)
        self.assertEqual(out, os.path.join(self.dir, ".vol", "tap_shock@0.40.wav"))
        self.assertEqual(read_wav(out), [400, -400, 12000, -12000, 0])
        mtime = os.path.getmtime(out)
        self.assertEqual(bridge.scaled_wav(self.wav, "0.4"), out)
        self.assertEqual(os.path.getmtime(out), mtime)

    def test_louder_clips_like_afplay(self):
        self.assertEqual(read_wav(bridge.scaled_wav(self.wav, 2)), [2000, -2000, 32767, -32768, 0])

    def test_a_changed_original_is_scaled_again(self):
        out = bridge.scaled_wav(self.wav, 0.5)
        write_wav(self.wav, [2000])
        os.utime(self.wav, (os.path.getmtime(out) + 5,) * 2)
        self.assertEqual(read_wav(bridge.scaled_wav(self.wav, 0.5)), [1000])

    def test_nonsense_volume_plays_the_original(self):
        self.assertEqual(bridge.scaled_wav(self.wav, "loud"), self.wav)

    def test_sounds_go_through_winsound(self):
        ws = types.SimpleNamespace(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4, PlaySound=mock.Mock())
        with mock.patch.object(bridge, "IS_WIN", True), mock.patch.dict(sys.modules, {"winsound": ws}), \
             mock.patch.object(bridge.subprocess, "Popen") as popen:
            bridge.Sounds()._start(self.wav, 0.5)
        popen.assert_not_called()
        ws.PlaySound.assert_called_once_with(os.path.join(self.dir, ".vol", "tap_shock@0.50.wav"), 7)


class WindowsStatusLine(unittest.TestCase):
    def test_line(self):
        data = {"model": {"display_name": "Opus"},
                "rate_limits": {"five_hour": {"used_percentage": 42.7}, "seven_day": {"used_percentage": 9}}}
        self.assertEqual(statusline.line(data), "Opus · 5h 42% · week 9%")
        self.assertEqual(statusline.line({}), "")

    def test_forwards_json_and_prints_even_without_a_bridge(self):
        raw = json.dumps({"model": {"display_name": "Opus"}}).encode()
        out = io.BytesIO()
        with mock.patch.object(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(raw))), \
             mock.patch.object(sys, "stdout", SimpleNamespace(buffer=out)), \
             mock.patch.object(statusline.urllib.request, "urlopen", side_effect=OSError("no bridge")) as up:
            statusline.main()
        self.assertEqual(out.getvalue(), "Opus\n".encode())
        self.assertEqual(up.call_args[0][0].data, raw)


class WindowsHooks(unittest.TestCase):
    def run_installer(self, *args):
        cfg = tempfile.mkdtemp()
        runtime = tempfile.mkdtemp()
        with mock.patch.object(install_hooks, "IS_WIN", True), mock.patch.object(install_hooks, "RUNTIME", runtime), \
             mock.patch.object(sys, "argv", ["install_hooks.py", "--config-dir", cfg, *args]), \
             mock.patch("builtins.print"):
            install_hooks.main()
        with open(os.path.join(cfg, "settings.json")) as f:
            return json.load(f), runtime, cfg

    def test_hooks_work_in_git_bash_and_powershell(self):
        settings, runtime, _ = self.run_installer()
        cmd = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertTrue(cmd.startswith("curl.exe "))
        self.assertNotIn("||", cmd)
        self.assertNotIn("/dev/null", cmd)
        self.assertNotIn("'", cmd)                                   # cmd-style quoting works in both shells
        self.assertIn("127.0.0.1:47823/hook", cmd)

    def test_status_line_is_the_python_one(self):
        settings, runtime, _ = self.run_installer()
        self.assertEqual(settings["statusLine"]["command"],
                         'py "{}"'.format(os.path.join(runtime, "statusline.py").replace("\\", "/")))
        self.assertTrue(os.path.exists(os.path.join(runtime, "statusline.py")))

    def test_uninstall_finds_windows_hooks(self):
        cfg = tempfile.mkdtemp(); runtime = tempfile.mkdtemp()
        for args in ((), ("--uninstall",)):
            with mock.patch.object(install_hooks, "IS_WIN", True), mock.patch.object(install_hooks, "RUNTIME", runtime), \
                 mock.patch.object(sys, "argv", ["install_hooks.py", "--config-dir", cfg, *args]), \
                 mock.patch("builtins.print"):
                install_hooks.main()
        with open(os.path.join(cfg, "settings.json")) as f:
            self.assertEqual(json.load(f), {})


class WindowsTimeZone(unittest.TestCase):
    def test_posix_rule_from_tzdata(self):
        try:
            import tzdata, tzlocal  # noqa: F401
        except ImportError:
            self.skipTest("tzdata/tzlocal not installed (the Windows bridge venv has them)")
        wifi = load("wifi_setup", "wifi_setup.py")
        with mock.patch.object(wifi.lump_ports, "IS_WIN", True), \
             mock.patch("tzlocal.get_localzone_name", return_value="Europe/Vienna"):
            self.assertEqual(wifi.posix_tz(), "CET-1CEST,M3.5.0,M10.5.0/3")

    def test_ssid_from_netsh(self):
        wifi = load("wifi_setup", "wifi_setup.py")
        out = ("    Name                   : WLAN\n    SSID                   : Buero-2G\n"
               "    BSSID                  : aa:bb:cc:dd:ee:ff\n")
        with mock.patch.object(wifi.lump_ports, "IS_WIN", True), \
             mock.patch.object(wifi.subprocess, "run", return_value=SimpleNamespace(stdout=out)):
            self.assertEqual(wifi.current_ssid(), "Buero-2G")


if __name__ == "__main__":
    unittest.main()
