# Projektinhalt: desk-buddy (Lump), Windows-Brücke

> Fork: `brummilab/desk-buddy` (Original: `joebentham/desk-buddy`).
> Lump ist eine Figur auf einem ESP32-S3-Display, die anzeigt, was die Claude-Sessions gerade tun.
> Ziel unserer Mitarbeit: Lump unter **Windows** betreiben.
> Diese Datei auch in den Obsidian-Vault übernehmen (in der Cloud-Session gab es keinen Vault-Zugriff).

## Stand

| Datum | Eintrag |
|---|---|
| 2026-11-13 | Grill-me-Befragung zur Windows-Brücke geführt, Stufe 1 umgesetzt (Branch `claude/friendly-curie-xs7i7b`). Mit Unit-Tests geprüft (101 Tests grün); auf echter Hardware noch nicht getestet, das Board ist bestellt. |
| 2026-11-13 | Entscheidung: Kein PR auf `main`, bis der Hardwaretest gelaufen ist. Danach Stufe 2 (Fokus) starten. |
| 2026-11-16 | Im Original gibt es einen offenen Windows-PR ([joebentham/desk-buddy#2](https://github.com/joebentham/desk-buddy/pull/2), von jakedev796): Brücke, Installer, Flashen, WLAN, **Fokus** und Tray-App „Lump Control“. **Entscheidung: auf PR #2 umschwenken.** Sein Stand liegt im Fork als Branch `windows-upstream-pr2`. Unsere eigene Version (dieser Branch) wird nicht weitergeführt. Gute Teile daraus schlägt David bei Bedarf im PR vor. |
| 2026-11-18 | Statische Zeile-für-Zeile-Prüfung von PR #2: keine Hinweise auf Schadcode, aber Stolpersteine für Firmen-Laptops (Hook-Befehl in PowerShell, Proxy für `127.0.0.1`, Constrained Language Mode, Datenverlust beim Speichern in Lump Control). Kommentartext für den PR liegt im Chat. |
| 2026-11-18 | Unser Branch wurde versehentlich in `main` gemergt ([brummilab/desk-buddy#1](https://github.com/brummilab/desk-buddy/pull/1)). Der Merge wird per Revert rückgängig gemacht. `main` = Original plus diese Datei. Unsere erste Version bleibt in der Historie (`06bc9fa`). |
| 2026-11-18 | Revert auf `main` gepusht (`c6b855a`). Korrekturen aus dem Review auf Branch **`windows-pr2-fixes`** (Basis: PR #2, Commit `369fae4`): Hooks ohne Shell (`curl.exe` in Exec-Form, `--noproxy`), kein Proxy für lokale Aufrufe (Statuszeile, Lump Control, OTA), Installer trennt die Tray-Pakete und weicht im Constrained Language Mode auf `.cmd` im Autostart aus, App-Liste wird beim Speichern nicht mehr gelöscht, sichere JSON-Schreibvorgänge, Log-Suche an allen drei Orten, Umlaut-SSIDs, Zeitzonen-Fehlercheck. Nur gelesen und auf Syntax geprüft, Tests nicht ausgeführt. **Hardwaretest jetzt mit `windows-pr2-fixes`.** |
| 2026-11-25 | **Hardwaretest unter Windows bestanden** (Details unten). Zertifikat-Fix für das Firmennetz eingebaut (`be10287`). |

## Setup (David)

- Windows mit **Claude Code nativ** (kein WSL), Python über den Launcher `py`
- Board ESP32-S3-LCD-1.3 (CH343-USB-Chip): bestellt, noch nicht da
- Keine eigene Statuszeile in Claude Code
- Aufgabenplanung (Task Scheduler) ist im Diakoniewerk erlaubt

## Entscheidungen (Grill-me, 2026-11-13)

1. **Stufenplan**
   - Stufe 1 (erledigt): Kern-Brücke. Hooks, Statuszeile, USB/WLAN, Sounds, Autostart, dazu Flashen und WLAN-Einrichtung.
   - Stufe 2: Fokus, also welche App vorne ist und welche Code-Session gerade angezeigt wird.
   - Stufe 3: Chat/Cowork über Windows UI Automation.
   - Nicht geplant: die Mac-Menüleisten-Figur (`lumpbar`).
2. **Autostart:** Aufgabenplanung bei Anmeldung, als eigener Benutzer, mit `pythonw` aus dem venv, Neustart bei Fehler jede Minute. Fallback: Verknüpfung im Autostart-Ordner. Kein Windows-Dienst, weil ein Dienst in Session 0 läuft und dort weder Sound noch Fokus möglich sind.
3. **Sound:** `winsound` aus der Standardbibliothek. Die Lautstärke wird über skalierte WAV-Kopien im Cache (`sounds\.vol\`) umgesetzt.
4. **Statuszeile:** eigene `tools/statusline.py`, weil Git for Windows kein `jq` mitbringt. Hooks nutzen `curl.exe` ohne `|| true`, damit sie in Git Bash **und** PowerShell laufen.
5. **USB-Erkennung:** Filter auf die USB-Kennung des CH343 (VID `0x1A86`, PIDs `0x55D2-55D5`, `0x55D8`), nicht auf beliebige COM-Ports. Ein fester Port lässt sich mit `serial_port` in `config.json` setzen.
6. **Flashen/WLAN:** `tools/flash.ps1`. `wifi_setup.py` läuft jetzt auf beiden Plattformen: SSID über `netsh`, Zeitzone über `tzlocal` + `tzdata`.
7. **Git:** Arbeit auf dem Branch, ohne direkten Push auf `main`. Der Code bleibt Upstream-fähig: macOS-Pfade sind unverändert, Windows kommt nur als zusätzlicher Zweig hinzu.

## Geänderte und neue Dateien (Stufe 1)

| Datei | Inhalt |
|---|---|
| `tools/lump_ports.py` (neu) | Port-Suche (macOS/Windows), festgelegter Port, Brücke für Flash/WLAN pausieren |
| `tools/install_bridge.ps1` (neu) | Windows-Installer: venv, Sounds, geplante Aufgabe `DeskBuddyBridge`, `-Uninstall` |
| `tools/flash.ps1` (neu) | Flashen unter Windows (`-NoArt`, `-Port`, `-Fast`) |
| `tools/statusline.py` (neu) | Statuszeile ohne jq |
| `tools/buddy_bridge.py` | Windows-Zweige: Port über `lump_ports`, winsound, ohne Fokus- und Slack-Abfrage, `pythonw`-sicher, kein doppelter Port-Bind |
| `tools/install_hooks.py` | Windows-Hook-Befehl und Python-Statuszeile |
| `tools/wifi_setup.py` | plattformneutral |
| `tools/install_bridge.sh` | kopiert zusätzlich `lump_ports.py` |
| `tests/test_windows.py` (neu) | 23 Tests mit Windows-Mocks |
| `README.md` | Abschnitt „Lump on Windows“ |

## Umschwenken auf PR #2 (2026-11-16)

- Branch `windows-upstream-pr2` = Stand von PR #2 (Commit `f52b259`, 14 Commits, etwa 3.600 Zeilen). Der Hardwaretest läuft **mit diesem Branch**.
- Pfade laut PR: Claude-App-Logs unter `%LOCALAPPDATA%\Claude\logs`, Session-Daten unter `%APPDATA%\Claude` (ich hatte für die Logs zuerst fälschlich `%APPDATA%` genannt).
- Anders als bei uns: Autostart über eine Verknüpfung im Autostart-Ordner plus `keepalive.py` statt Aufgabenplanung. Installer `tools\windows\install.ps1`, Flashen `tools\windows\flash.ps1`.
- Zusätzliche pip-Pakete: `psutil`, `pystray`, `pillow`, `pywebview` (Fenster über WebView2).
- **Statische Prüfung (2026-11-16):** Netzwerk nur `127.0.0.1` (Brücke 47823, Lump Control 47825 lokal). Keine Downloads außer pip-Paketen von PyPI. Kein Base64- oder Encoded-Command-Trick, keine Registry-Änderungen. Schreibt nur nach `~\.desk-buddy`, in den Autostart-Ordner und in `settings.json` (Hooks). Die Tests von PR #2 wurden in der Cloud **nicht ausgeführt** (fremder Code, blockiert).
- Stufe 2 (Fokus) steckt bereits in PR #2. Unsere eigene Stufe 2 entfällt.
- Wenn wir als Erweiterung vorschlagen wollen: Absicherung gegen eine doppelt gestartete Brücke (`allow_reuse_address` unter Windows, bei PR #2 per `keepalive.py`-Portcheck gelöst), Aufgabenplanung als Alternative.

## Hardwaretest Windows (2026-11-25), Branch `windows-pr2-fixes`: bestanden

- [x] Dienstrechner: kein Proxy (WinHTTP), `FullLanguage`, keine Execution Policy per GPO, PowerShell ohne Adminrechte
- [x] Board erkannt: `USB\VID_1A86&PID_55D3` auf **COM4**, Windows-eigener Treiber. **Erst nach Kabeltausch.** Die ersten beiden USB-C-Kabel waren reine Ladekabel: Das Display leuchtete, aber Windows sah kein Gerät.
- [x] Flashen mit `flash.ps1` (ohne Bremse, die Zeichnungen in 41 s). **Firmennetz:** pip bzw. PlatformIO scheiterten an `CERTIFICATE_VERIFY_FAILED` (TLS-Inspection). Gelöst mit dem Export der Windows-Zertifikate; jetzt fest eingebaut (`tools/windows/ca_bundle.py`, Commit `be10287`). PlatformIO zog `espressif32@8.0.0`, der Build ist ok.
- [x] `install.ps1`: Brücke und Lump Control (WebView2) laufen, Autostart über Verknüpfungen (kein `.cmd`-Ausweichweg nötig)
- [x] `install_hooks.py` mit dem Python aus dem venv: Hooks in Exec-Form (`curl.exe`) kommen an
- [x] Arbeiten → Feiern ✔, Rückfrage (`PermissionRequest`) → alert ✔, Nutzungsfarbe aus der Desktop-App (Woche 97 % → rot) ✔
- [x] Klopfen: Sensor gefunden (`imu=on`). Braucht einen kräftigen Klopfer (Schwelle 0,35 g, gemessen 0,43 g), in Lump Control anpassbar. Gag (Disco) mit Ton ✔
- **Wichtig:** Cloud-Sitzungen (claude.ai/code, wie diese Chat-Sitzung) lösen **keine** Hooks auf dem Laptop aus. Nur lokale Claude-Code-Sitzungen treiben Lump.
- Auffällig: Die Claude-App speichert ihre Daten unter `AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc`. Die Brücke führt das als zweites Konto `claude-pzs8sxrjxfjjc`; prüfen, ob das stört.

## Noch offen

- [ ] Fokus-Erkennung testen: Wechsel in eine fertige Session → „unseen“ sollte verschwinden
- [ ] Lump Control offen lassen und abmelden: Blockiert es das Abmelden?
- [ ] Nach dem Neuanmelden: Startet die Brücke von selbst?
- [ ] WLAN (nicht mit dem Firmen-WLAN; das Passwort liegt unverschlüsselt auf dem Board)
- [ ] Rückmeldung an den Autor von PR #2 (Testergebnis und Korrekturen)

## Nächste Stufen

- **Stufe 2 (Fokus):** steckt in PR #2; Test steht noch aus (siehe „Noch offen“).
- **Stufe 3 (Chat/Cowork):** UI-Automation-Baum der Windows-Claude-App (Electron) untersuchen und ein Python-Helfer, der dieselbe JSON an `/app` schickt wie der Swift-Helfer.
