# Build + flash the desk-buddy firmware over a USB data cable on Windows: flash.sh's twin.
# Day to day, use tools\ota.py instead: it updates him over Wi-Fi, sending only what changed.
# This is for the first install of a new partition layout, or recovery when Wi-Fi updates can't reach him.
# Writes the bootloader, partition table, program (slot app0, made the boot slot) and, unless -NoArt,
# his drawings (firmware\data\lump.bin) into the "lump" partition.
#
#   powershell -ExecutionPolicy Bypass -File tools\flash.ps1             # everything (drawings: minutes)
#   powershell -ExecutionPolicy Bypass -File tools\flash.ps1 -NoArt      # program only
#   ... -Port COM7      pick the port yourself (otherwise tools\lump_ports.py finds it)
#   ... -Fast           plain esptool, no pacing: macOS needs the pacing, Windows may not (try it)
#
# Needs: PlatformIO's "pio" on PATH (py -m pip install platformio), and Python 3 ("py"); esptool goes
# into tools\.venv the first time.
param([switch]$NoArt, [string]$Port = "", [switch]$Fast)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Venv = if ($env:VENV) { $env:VENV } else { Join-Path $Root "tools\.venv" }
$Py = Join-Path $Venv "Scripts\python.exe"
$Task = "DeskBuddyBridge"                       # must match TASK in tools/lump_ports.py

if (-not (Test-Path $Py)) {
    & py -3 -m venv $Venv; if ($LASTEXITCODE) { throw "making $Venv failed" }
    & $Py -m pip -q install --disable-pip-version-check esptool pyserial
    if ($LASTEXITCODE) { throw "installing esptool failed" }
}
if (-not (Get-Command pio -ErrorAction SilentlyContinue)) { throw "PlatformIO's 'pio' isn't on PATH: py -m pip install platformio" }

# the bridge holds the serial port (on Windows nobody else may open it): pause it while flashing
$bridge = Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
if ($bridge) { Stop-ScheduledTask -TaskName $Task; Start-Sleep -Seconds 1 }
try {
    if (-not $Port) {
        $Port = (& $Py (Join-Path $Root "tools\lump_ports.py") | Select-Object -First 1)
        if (-not $Port) {
            & $Py (Join-Path $Root "tools\lump_ports.py") -v | Out-Null
            throw "No port with Lump's USB ids found (list above). Is he plugged in with a data cable? Or pass -Port COMx."
        }
    }
    Write-Host "Flashing on $Port"

    Push-Location (Join-Path $Root "firmware")
    try { & pio run; if ($LASTEXITCODE) { throw "pio run failed" } } finally { Pop-Location }

    $B = Join-Path $Root "firmware\.pio\build\buddy"
    $BootApp0 = Join-Path $env:USERPROFILE ".platformio\packages\framework-arduinoespressif32\tools\partitions\boot_app0.bin"
    $ArtAddr = "0x410000"                       # the "lump" partition in firmware\partitions_lump.csv
    $images = @("0x0", "$B\bootloader.bin", "0x8000", "$B\partitions.bin", "0xe000", $BootApp0, "0x10000", "$B\firmware.bin")
    if (-not $NoArt) { $images += @($ArtAddr, (Join-Path $Root "firmware\data\lump.bin")) }
    $write = @("--chip", "esp32s3", "--port", $Port, "--baud", "921600", "write_flash", "--flash_mode", "dio", "--flash_size", "16MB") + $images
    if ($Fast) {
        & $Py -I -m esptool @write
    } else {
        & $Py -I (Join-Path $Root "tools\paced_esptool.py") --no-stub @write
    }
    if ($LASTEXITCODE) { throw "esptool failed" }
} finally {
    if ($bridge) { Start-ScheduledTask -TaskName $Task }
}
