# Install (or update) the Desk Buddy bridge on Windows: install_bridge.sh's twin.
#   DeskBuddyBridge   scheduled task, at logon, as you: the Python bridge (Claude Code hooks -> Lump
#                     over USB or Wi-Fi). Restarted within a minute if it ever stops.
# Not on Windows (yet): the app watcher (Chat/Cowork state) and knowing which app is in front.
# Runtime lives in %USERPROFILE%\.desk-buddy:
#   venv\  bridge.py  lump_ports.py  bridge.log  bridge.out  sounds\
# Needs: Python 3 from python.org or winget (the "py" launcher). No admin rights.
#
#   powershell -ExecutionPolicy Bypass -File tools\install_bridge.ps1
#   powershell -ExecutionPolicy Bypass -File tools\install_bridge.ps1 -Uninstall
param([switch]$Uninstall)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RT = Join-Path $env:USERPROFILE ".desk-buddy"
$Task = "DeskBuddyBridge"                       # must match TASK in tools/lump_ports.py
$Startup = Join-Path ([Environment]::GetFolderPath("Startup")) "Desk Buddy bridge.lnk"

function Stop-Bridge {
    if (Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $Task -Confirm:$false
    }
    # a bridge started some other way (the Startup-folder fallback below, or by hand) holds the port too
    Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'" |
        Where-Object { $_.CommandLine -like "*\.desk-buddy\bridge.py*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Remove-Item $Startup -ErrorAction SilentlyContinue
}

Stop-Bridge
if ($Uninstall) {
    Write-Host "Bridge removed (runtime left in $RT)."
    exit 0
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "The Python launcher 'py' wasn't found. Install Python 3: winget install Python.Python.3.12"
}
New-Item -ItemType Directory -Force -Path $RT | Out-Null
$Py = Join-Path $RT "venv\Scripts\python.exe"
$PyW = Join-Path $RT "venv\Scripts\pythonw.exe"
if (-not (Test-Path $Py)) { & py -3 -m venv (Join-Path $RT "venv"); if ($LASTEXITCODE) { throw "making the venv failed" } }
& $Py -m pip -q install --disable-pip-version-check --upgrade pip
& $Py -m pip -q install --disable-pip-version-check pyserial icalendar recurring-ical-events tzlocal tzdata
if ($LASTEXITCODE) { throw "pip install failed" }
Copy-Item (Join-Path $Root "tools\buddy_bridge.py") (Join-Path $RT "bridge.py") -Force
Copy-Item (Join-Path $Root "tools\lump_ports.py") (Join-Path $RT "lump_ports.py") -Force
# Lump's voice: renders the WAVs, and installs sounds.json (which moments make a noise) the first time.
& $Py (Join-Path $Root "tools\make_sounds.py")
# ...and the sound effects for his tap gags (tap_<gag>.wav), timed to the drawings in design/lump.html.
& $Py (Join-Path $Root "tools\make_gag_sounds.py")

# pythonw: no console window. KeepAlive's stand-in: restart every minute if it stops, never time out,
# never two at once, and keep running on battery.
$action = New-ScheduledTaskAction -Execute $PyW -Argument "-u `"$(Join-Path $RT 'bridge.py')`"" -WorkingDirectory $RT
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
try {
    Register-ScheduledTask -TaskName $Task -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
        -Description "Desk Buddy: Claude Code -> Lump (tools/install_bridge.ps1)" | Out-Null
    Start-ScheduledTask -TaskName $Task
} catch {
    # Some managed PCs don't let a normal user add a logon task. A Startup-folder shortcut still starts
    # him at logon, just without the restart-if-it-stops (the bridge rarely needs it).
    Write-Warning "Couldn't add the scheduled task ($($_.Exception.Message)). Using the Startup folder instead."
    $sh = (New-Object -ComObject WScript.Shell).CreateShortcut($Startup)
    $sh.TargetPath = $PyW
    $sh.Arguments = "-u `"$(Join-Path $RT 'bridge.py')`""
    $sh.WorkingDirectory = $RT
    $sh.Save()
    Start-Process -FilePath $PyW -ArgumentList "-u", "`"$(Join-Path $RT 'bridge.py')`"" -WorkingDirectory $RT
    Write-Warning "tools\wifi_setup.py and tools\flash.ps1 can't pause a bridge started this way: quit it first (re-run this with -Uninstall)."
}

Start-Sleep -Seconds 3
try {
    Invoke-RestMethod -TimeoutSec 2 http://127.0.0.1:47823/status | ConvertTo-Json -Depth 4
    Write-Host "Bridge running. Next: py tools\install_hooks.py"
} catch {
    Write-Warning "The bridge didn't answer on 127.0.0.1:47823. Look in $RT\bridge.out and $RT\bridge.log."
}
