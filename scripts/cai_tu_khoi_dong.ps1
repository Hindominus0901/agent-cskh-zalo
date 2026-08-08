# Dang ky bot chay tu dong moi khi dang nhap Windows.
#
#   .\scripts\cai_tu_khoi_dong.ps1          cai dat
#   .\scripts\cai_tu_khoi_dong.ps1 -Go      go bo
#   .\scripts\cai_tu_khoi_dong.ps1 -Xem     xem trang thai
#
# Khong can quyen admin — tao tac vu o cap nguoi dung.

param(
    [switch]$Go,
    [switch]$Xem
)

$ErrorActionPreference = "Stop"
$TEN = "ZaloAgentBot"
$goc = Split-Path $PSScriptRoot -Parent
$runps1 = Join-Path $goc "run.ps1"

if ($Xem) {
    $t = Get-ScheduledTask -TaskName $TEN -ErrorAction SilentlyContinue
    if (-not $t) { Write-Host "Chua cai dat."; exit 0 }
    $info = Get-ScheduledTaskInfo -TaskName $TEN
    Write-Host "Trang thai      : $($t.State)"
    Write-Host "Chay lan cuoi   : $($info.LastRunTime)"
    Write-Host "Ket qua lan cuoi: $($info.LastTaskResult)"
    Write-Host "Lan chay ke tiep: $($info.NextRunTime)"
    exit 0
}

if ($Go) {
    Unregister-ScheduledTask -TaskName $TEN -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Da go bo tac vu '$TEN'."
    exit 0
}

if (-not (Test-Path $runps1)) { throw "Khong thay $runps1" }

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runps1`"" `
    -WorkingDirectory $goc

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask -TaskName $TEN -Action $action -Trigger $trigger `
    -Settings $settings -Description "Zalo AI Agent — tro ly AI tren Zalo" -Force | Out-Null

Write-Host "Da cai dat tac vu '$TEN'."
Write-Host ""
Write-Host "Bot se tu chay moi khi ban dang nhap Windows, va tu khoi dong lai neu chet."
Write-Host ""
Write-Host "Chay ngay bay gio     : Start-ScheduledTask -TaskName $TEN"
Write-Host "Dung                  : Stop-ScheduledTask -TaskName $TEN"
Write-Host "Xem trang thai        : .\scripts\cai_tu_khoi_dong.ps1 -Xem"
Write-Host "Go bo                 : .\scripts\cai_tu_khoi_dong.ps1 -Go"
Write-Host ""
Write-Host "LUU Y: bot chi chay khi may BAT va ban DA DANG NHAP. Tat may la bot chet"
Write-Host "va tin nhan gui trong luc do se mat (Zalo khong luu lai). Muon chay 24/7"
Write-Host "that su thi can VPS — xem docs/05-chuyen-len-vps.md"
