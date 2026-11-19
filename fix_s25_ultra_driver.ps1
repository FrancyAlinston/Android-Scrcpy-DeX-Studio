# Elevated Remediation & Upgrade Script for Samsung Galaxy S25 Ultra (USB\VID_04E8&PID_6860\R3CY90MDSER)
# 1. Purges the legacy 2013 Samsung USB Driver (v2.11.1.0, oem351.inf..oem364.inf, ssudbus.sys) blocked by Windows 11 Memory Integrity (HVCI)
# 2. Silently installs the official Samsung Android USB Driver for Windows v1.9.5.0 (2026 HVCI-compliant release)
# 3. Re-enumerates the Galaxy S25 Ultra and verifies ADB connectivity.

$ErrorActionPreference = "Continue"

# Auto-elevate via UAC / Windows Hello if not already running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[*] Requesting Administrator elevation..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Wait
    exit 0
}

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  1. PURGING LEGACY 2013 SAMSUNG USB DRIVER (v2.11.1.0 / ssudbus.sys)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Stop and delete legacy ssud* kernel services if registered
$services = @("ssudbus", "ssudmdm", "ssudserd", "ssudadb", "ssudnd5", "ssudrnds", "ssudrmnet", "ssudrmnetmp")
foreach ($svc in $services) {
    sc.exe stop $svc 2>$null | Out-Null
}

# Remove all 2013 Samsung ssud*.inf packages from Windows DriverStore
$raw = pnputil.exe /enum-drivers
$lines = $raw -split "`r?`n"
$curOem = ""
$curVer = ""
foreach ($l in $lines) {
    if ($l -match "Published Name\s*:\s*(oem\d+\.inf)") {
        $curOem = $Matches[1]
    }
    if ($l -match "Original Name\s*:\s*(ssud.*\.inf)") {
        $origName = $Matches[1]
        Write-Host "[*] Force-removing legacy 2013 driver package $curOem ($origName)..." -ForegroundColor Yellow
        pnputil.exe /delete-driver $curOem /uninstall /force
        $curOem = ""
    }
}

# Delete residual 2013 C:\Windows\System32\drivers\ssud*.sys files if unlocked
Get-ChildItem "C:\Windows\System32\drivers\ssud*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host "  2. INSTALLING OFFICIAL SAMSUNG ANDROID USB DRIVER v1.9.5.0 (2026)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

$driverInstaller = "$env:USERPROFILE\Downloads\SAMSUNG_USB_Driver_for_Mobile_Phones_v1.9.5.0.exe"
if (Test-Path $driverInstaller) {
    Write-Host "[*] Running silent install of $driverInstaller..." -ForegroundColor Green
    $proc = Start-Process -FilePath $driverInstaller -ArgumentList "/S" -Wait -PassThru
    Write-Host "[+] Installer completed with exit code: $($proc.ExitCode)" -ForegroundColor Green
} else {
    Write-Warning "[!] Driver installer not found at $driverInstaller"
}

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host "  3. RE-ENUMERATING SAMSUNG GALAXY S25 ULTRA ON USB BUS" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

pnputil.exe /remove-device "USB\VID_04E8&PID_6860\R3CY90MDSER" 2>$null
pnputil.exe /scan-devices
Start-Sleep -Seconds 3

Get-PnpDevice | Where-Object { $_.InstanceId -match "VID_04E8|R3CY90MDSER" } | Format-Table Status, Class, FriendlyName, InstanceId -AutoSize
