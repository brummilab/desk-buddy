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

## Offene Punkte / zu testen, sobald das Board da ist

- [ ] Mit Branch `windows-pr2-fixes`: `tools\windows\install.ps1`, `tools\windows\flash.ps1`, `install_hooks.py`
- [ ] Auf dem Dienstrechner prüfen: `netsh winhttp show proxy`, `$ExecutionContext.SessionState.LanguageMode`, `Get-ExecutionPolicy -List`
- [ ] Erkennt PR #2 den CH343? Er erwartet genau `1A86:55D3`. Kennung prüfen mit `py -m serial.tools.list_ports -v`
- [ ] `flash.ps1` mit Pacing, danach `-Fast` testen. Braucht Windows das Pacing überhaupt?
- [ ] `install_bridge.ps1`: Lässt sich die geplante Aufgabe ohne Adminrechte anlegen?
- [ ] Hooks kommen an (`curl 127.0.0.1:47823/status` während einer Session)
- [ ] Sounds hörbar, Lautstärke wirkt, Gag-Sounds synchron (`AFPLAY_LAG` ggf. anpassen)
- [ ] WLAN: Wird `lump.local` aufgelöst? Stimmt die Zeitzone (Uhrzeit, Nachtmodus)?
- [ ] Die `.ps1`-Skripte wurden in der Cloud nicht ausgeführt (dort gibt es kein PowerShell). Erster echter Lauf bei David.

## Nächste Stufen

- **Stufe 2 (Fokus):** vordere App über `GetForegroundWindow` + Prozessname (ctypes). Session-Fokus aus dem Log der Windows-Claude-App (`%APPDATA%\Claude\logs`?) und `claude-code-sessions`. Pfade erst auf echtem Windows prüfen.
- **Stufe 3 (Chat/Cowork):** UI-Automation-Baum der Windows-Claude-App (Electron) untersuchen und ein Python-Helfer, der dieselbe JSON an `/app` schickt wie der Swift-Helfer.
