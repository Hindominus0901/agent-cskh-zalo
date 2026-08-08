# Khoi dong bot. Tu tim uv, tu khoi dong lai neu bot chet.
#
#   .\run.ps1              chay binh thuong
#   .\run.ps1 -Once        chay mot lan, khong tu khoi dong lai (de xem loi)
#   .\run.ps1 -Check       chi kiem tra cau hinh roi thoat

param(
    [switch]$Once,
    [switch]$Check
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Uv {
    foreach ($p in @(
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\uv.exe",
        "$env:USERPROFILE\.local\bin\uv.exe"
    )) {
        if (Test-Path $p) { return $p }
    }
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $found = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse `
        -Filter uv.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { return $found.FullName }
    throw "Khong tim thay uv. Cai bang: winget install --id=astral-sh.uv -e --scope user"
}

$uv = Find-Uv

if ($Check) {
    & $uv run agent-cskh check
    exit $LASTEXITCODE
}

if ($Once) {
    & $uv run agent-cskh chay
    exit $LASTEXITCODE
}

# Vong tu khoi dong lai. Bot da tu chiu duoc loi mang va loi Zalo ben trong;
# vong nay chi de cuu nhung truong hop tien trinh chet han (het bo nho, Windows
# ngu day, Python crash).
$lan = 0
while ($true) {
    $lan++
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Khoi dong bot (lan $lan)..."
    & $uv run agent-cskh chay
    $code = $LASTEXITCODE

    if ($code -eq 0) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Bot dung binh thuong."
        break
    }

    # Cho lau dan de khong quay vong dot CPU khi loi lap lai (5s -> toi da 5 phut).
    $cho = [Math]::Min(300, 5 * [Math]::Pow(2, [Math]::Min($lan - 1, 6)))
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Bot thoat voi ma $code. Chay lai sau $cho giay."
    Start-Sleep -Seconds $cho
}
