$DesktopPath = [Environment]::GetFolderPath("Desktop")
$TargetLnk = Join-Path $DesktopPath "MediTrack ERP.lnk"
$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$TargetPath = Join-Path $CurrentDir "run.bat"
$DistExe = Join-Path $CurrentDir "dist\MediTrack\MediTrack.exe"
if (Test-Path $DistExe) {
    $TargetPath = $DistExe
}

$IconPath = Join-Path $CurrentDir "assets\icon.ico"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($TargetLnk)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $CurrentDir
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
$Shortcut.Description = "MediTrack Medical Shop & Pharmacy ERP System"
$Shortcut.Save()

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " [SUCCESS] Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host " Target:   $TargetPath" -ForegroundColor White
Write-Host " Shortcut: $TargetLnk" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
