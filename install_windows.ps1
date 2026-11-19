# Windows System Installer for J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0
$ErrorActionPreference = "Stop"

$srcDir = "c:\Users\franc\Pictures\Projects\iRipper\Mobile Engineering Studio\adb-scrcpy-studio"
# Primary install in %LOCALAPPDATA%\Programs so Windows appresolver.dll enables 'Pin to Start' (which blocks 'Program Files' substring paths)
$installDir = "$env:LOCALAPPDATA\Programs\Android Scrcpy DeX Studio"
$mirrorDir = "H:\Program Files\Android Scrcpy DeX Studio"
$exePath = Join-Path $installDir "AndroidScrcpyDeXStudio.exe"
$setupPath = Join-Path $installDir "AndroidScrcpyDeXStudio-Setup-v2.0.exe"
$iconPath = Join-Path $installDir "android_scrcpy_dex.ico"
$pngPath = Join-Path $installDir "android_scrcpy_dex.png"
$appDataDir = "$env:LOCALAPPDATA\AndroidScrcpyDeXStudio"

Write-Host ">>> Installing J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.2 to: $installDir" -ForegroundColor Cyan

# 1. Stop any running instance before updating binary
Get-Process -Name "AndroidScrcpyDeXStudio" -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Create target directories
foreach ($d in @($installDir, $mirrorDir, $appDataDir)) {
    if (!(Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}

# 3. Copy self-contained application binaries & icon assets
Write-Host ">>> Deploying self-contained single-file binaries and icons..." -ForegroundColor Cyan
foreach ($dest in @($installDir, $mirrorDir)) {
    Copy-Item -Path "$srcDir\dist\AndroidScrcpyDeXStudio.exe" -Destination (Join-Path $dest "AndroidScrcpyDeXStudio.exe") -Force
    Copy-Item -Path "$srcDir\dist\AndroidScrcpyDeXStudio-Setup-v2.0.exe" -Destination (Join-Path $dest "AndroidScrcpyDeXStudio-Setup-v2.0.exe") -Force
    Copy-Item -Path "$srcDir\assets\android_scrcpy_dex.ico" -Destination (Join-Path $dest "android_scrcpy_dex.ico") -Force
    Copy-Item -Path "$srcDir\assets\android_scrcpy_dex.png" -Destination (Join-Path $dest "android_scrcpy_dex.png") -Force
}
Copy-Item -Path "$srcDir\assets\android_scrcpy_dex.ico" -Destination (Join-Path $appDataDir "android_scrcpy_dex.ico") -Force

# Ensure HKCU\Software\Classes\lnkfile\shellex\ContextMenuHandlers\PintoStartScreen is registered
$pinKey = "HKCU:\Software\Classes\lnkfile\shellex\ContextMenuHandlers\PintoStartScreen"
if (!(Test-Path $pinKey)) {
    New-Item -Path $pinKey -Force | Out-Null
}
Set-ItemProperty -Path $pinKey -Name "(default)" -Value "{470C0EBD-5D73-4d58-9CED-E91E22E23282}"

# Also keep Downloads copy updated
if (Test-Path "$env:USERPROFILE\Downloads") {
    Copy-Item -Path "$srcDir\dist\AndroidScrcpyDeXStudio.exe" -Destination "$env:USERPROFILE\Downloads\AndroidScrcpyDeXStudio.exe" -Force
    Copy-Item -Path "$srcDir\dist\AndroidScrcpyDeXStudio-Setup-v2.0.exe" -Destination "$env:USERPROFILE\Downloads\AndroidScrcpyDeXStudio-Setup-v2.0.exe" -Force
}

# 4. Create Start Menu Shortcut
$startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Android & Scrcpy DeX Studio.lnk"
Write-Host ">>> Creating Start Menu Shortcut: $startMenuPath" -ForegroundColor Cyan
$wsh = New-Object -ComObject WScript.Shell
$scStart = $wsh.CreateShortcut($startMenuPath)
$scStart.TargetPath = $exePath
$scStart.WorkingDirectory = $installDir
$scStart.IconLocation = "$iconPath,0"
$scStart.Description = "J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0 - ADB, Task Manager, Scrcpy 4.0 & PC DeX Mode"
$scStart.Save()

# 5. Create Desktop Shortcut
$desktopPath = [System.IO.Path]::Combine([System.Environment]::GetFolderPath("Desktop"), "Android & Scrcpy DeX Studio.lnk")
Write-Host ">>> Creating Desktop Shortcut: $desktopPath" -ForegroundColor Cyan
$scDesk = $wsh.CreateShortcut($desktopPath)
$scDesk.TargetPath = $exePath
$scDesk.WorkingDirectory = $installDir
$scDesk.IconLocation = "$iconPath,0"
$scDesk.Description = "J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0 - ADB, Task Manager, Scrcpy 4.0 & PC DeX Mode"
$scDesk.Save()

# 6. Create Uninstaller Script
$uninstallScript = Join-Path $installDir "uninstall.ps1"
$uninstallLines = @(
    '$ErrorActionPreference = "SilentlyContinue"',
    'Stop-Process -Name "AndroidScrcpyDeXStudio" -Force',
    "Remove-Item -Path '$startMenuPath' -Force",
    "Remove-Item -Path '$desktopPath' -Force",
    'Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AndroidScrcpyDeXStudio" -Recurse -Force',
    'Write-Host "J.A.R.V.I.S. Android & Scrcpy DeX Studio has been uninstalled from Windows." -ForegroundColor Green'
)
$uninstallLines -join "`r`n" | Set-Content -Path $uninstallScript -Force

# 7. Register in Windows "Installed apps" / "Add or Remove Programs"
Write-Host ">>> Registering in Windows Installed Apps (Registry)..." -ForegroundColor Cyan
$regKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AndroidScrcpyDeXStudio"
if (!(Test-Path $regKey)) {
    New-Item -Path $regKey -Force | Out-Null
}

$sizeKb = [int]((Get-ChildItem -Path $installDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1KB)

Set-ItemProperty -Path $regKey -Name "DisplayName" -Value "J.A.R.V.I.S. Android & Scrcpy DeX Studio"
Set-ItemProperty -Path $regKey -Name "DisplayVersion" -Value "3.0.0"
Set-ItemProperty -Path $regKey -Name "Publisher" -Value "J.A.R.V.I.S. Mobile Engineering Studio"
Set-ItemProperty -Path $regKey -Name "DisplayIcon" -Value "$iconPath,0"
Set-ItemProperty -Path $regKey -Name "InstallLocation" -Value $installDir
Set-ItemProperty -Path $regKey -Name "InstallDate" -Value (Get-Date -Format "yyyyMMdd")
Set-ItemProperty -Path $regKey -Name "UninstallString" -Value "powershell.exe -ExecutionPolicy Bypass -NoProfile -File `"$uninstallScript`""
Set-ItemProperty -Path $regKey -Name "EstimatedSize" -Value $sizeKb -Type DWord
Set-ItemProperty -Path $regKey -Name "NoModify" -Value 1 -Type DWord
Set-ItemProperty -Path $regKey -Name "NoRepair" -Value 1 -Type DWord
Set-ItemProperty -Path $regKey -Name "Comments" -Value "Self-Contained Android ADB Control, Live Task Manager, Scrcpy 4.0 Mirror & PC DeX Workstation"

# 8. Launch Installed Studio
Write-Host ">>> Launching J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0..." -ForegroundColor Green
Start-Process -FilePath $exePath -WorkingDirectory $installDir

Write-Host ">>> J.A.R.V.I.S. Android & Scrcpy DeX Studio v2.0 is now installed and running!" -ForegroundColor Green
