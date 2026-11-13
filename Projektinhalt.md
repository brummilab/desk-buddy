# Projektinhalt: desk-buddy (Lump), Windows-Brücke

> Fork: `brummilab/desk-buddy` (Original: `joebentham/desk-buddy`).
> Lump ist eine Figur auf einem ESP32-S3-Display, die anzeigt, was die Claude-Sessions gerade tun.
> Ziel unserer Mitarbeit: Lump unter **Windows** betreiben.
> Diese Datei auch in den Obsidian-Vault übernehmen (in der Cloud-Session gab es keinen Vault-Zugriff).

## Stand

| Datum | Eintrag |
|---|---|
| 2026-11-13 | Grill-me-Befragung zur Windows-Brücke geführt, Stufe 1 umgesetzt (Branch `claude/friendly-curie-xs7i7b`). Mit Unit-Tests geprüft (101 Tests grün); auf echter Hardware noch nicht getestet, das Board ist bestellt. |

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

## Offene Punkte / zu testen, sobald das Board da ist

- [ ] `py tools\lump_ports.py -v`: Wird der CH343 erkannt, und mit welcher PID?
- [ ] `flash.ps1` mit Pacing, danach `-Fast` testen. Braucht Windows das Pacing überhaupt?
- [ ] `install_bridge.ps1`: Lässt sich die geplante Aufgabe ohne Adminrechte anlegen?
- [ ] Hooks kommen an (`curl 127.0.0.1:47823/status` während einer Session)
- [ ] Sounds hörbar, Lautstärke wirkt, Gag-Sounds synchron (`AFPLAY_LAG` ggf. anpassen)
- [ ] WLAN: Wird `lump.local` aufgelöst? Stimmt die Zeitzone (Uhrzeit, Nachtmodus)?
- [ ] Die `.ps1`-Skripte wurden in der Cloud nicht ausgeführt (dort gibt es kein PowerShell). Erster echter Lauf bei David.

## Nächste Stufen

- **Stufe 2 (Fokus):** vordere App über `GetForegroundWindow` + Prozessname (ctypes). Session-Fokus aus dem Log der Windows-Claude-App (`%APPDATA%\Claude\logs`?) und `claude-code-sessions`. Pfade erst auf echtem Windows prüfen.
- **Stufe 3 (Chat/Cowork):** UI-Automation-Baum der Windows-Claude-App (Electron) untersuchen und ein Python-Helfer, der dieselbe JSON an `/app` schickt wie der Swift-Helfer.
