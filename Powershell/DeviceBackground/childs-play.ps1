<# 
    childs-play.ps1
    Lightweight Windows host health + triage collector.

    Captures:
      - running processes (tasklist + Get-Process)
      - ipconfig /all
      - ARP cache
      - netstat
      - directory listings (root and user profile)
      - whoami /all
      - systeminfo
      - nslookup (self + microsoft.com)
      - gpresult /r (user & computer)
      - route print
      - net user + local admin group

    Output:
      %USERPROFILE%\Desktop\childs_play\<COMPUTERNAME>_<yyyyMMdd-HHmmss>\*
      Also creates a ZIP of the folder.

    Usage:
      Right-click > Run with PowerShell (will prompt for elevation) 
      OR: powershell.exe -ExecutionPolicy Bypass -File .\childs-play.ps1
#>

#region Elevation check & relaunch
function Test-IsAdmin {
    try {
        $current = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($current)
        return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch { return $false }
}

if (-not (Test-IsAdmin)) {
    Write-Host "[*] Elevation required. Relaunching as Administrator..."
    $psi = @{
        FilePath = "powershell.exe"
        ArgumentList = @("-NoProfile","-ExecutionPolicy","Bypass","-File","`"$PSCommandPath`"")
        Verb = "RunAs"
        WindowStyle = "Hidden"
    }
    try {
        Start-Process @psi
        exit
    } catch {
        Write-Error "Failed to relaunch elevated: $($_.Exception.Message)"
        exit 1
    }
}
#endregion

#region Prep output paths
$ErrorActionPreference = 'Stop'
$computer = $env:COMPUTERNAME
$ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
$base = Join-Path $env:USERPROFILE "Desktop\childs_play"
$outDir = Join-Path $base "$computer`_$ts"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$transcript = Join-Path $outDir "childs_play_transcript.txt"
Start-Transcript -Path $transcript -Force | Out-Null

# Helper: run a command and save stdout + stderr to a file
function Run-ToFile {
    param(
        [Parameter(Mandatory)]
        [string]$Command,
        [Parameter(Mandatory)]
        [string]$Args,
        [Parameter(Mandatory)]
        [string]$OutFile
    )
    Write-Host "[*] $Command $Args"
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Command
        $psi.Arguments = $Args
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $p = [System.Diagnostics.Process]::Start($psi)
        $stdout = $p.StandardOutput.ReadToEnd()
        $stderr = $p.StandardError.ReadToEnd()
        $p.WaitForExit()

        "# $Command $Args`n" | Out-File -FilePath $OutFile -Encoding UTF8
        if ($stdout) { $stdout | Out-File -FilePath $OutFile -Append -Encoding UTF8 }
        if ($stderr) { "`n--- STDERR ---`n$stderr" | Out-File -FilePath $OutFile -Append -Encoding UTF8 }
    } catch {
        "ERROR running $Command $Args : $($_.Exception.Message)" | Out-File -FilePath $OutFile -Encoding UTF8
    }
}

# Helper: run PowerShell and save structured output
function PS-ToFile {
    param(
        [Parameter(Mandatory)][scriptblock]$ScriptBlock,
        [Parameter(Mandatory)][string]$OutFile
    )
    Write-Host "[*] PS: $OutFile"
    try {
        $result = & $ScriptBlock
        "# PowerShell Output`n" | Out-File -FilePath $OutFile -Encoding UTF8
        $result | Out-String | Out-File -FilePath $OutFile -Append -Encoding UTF8
    } catch {
        "ERROR: $($_.Exception.Message)" | Out-File -FilePath $OutFile -Encoding UTF8
    }
}
#endregion

#region System snapshot header
$header = @"
childs-play host snapshot
Computer : $computer
User     : $env:USERNAME
Time     : $(Get-Date -Format u)
OS       : $([System.Environment]::OSVersion.VersionString)
PS       : $($PSVersionTable.PSVersion)
"@
$header | Out-File -FilePath (Join-Path $outDir "_summary.txt") -Encoding UTF8
#endregion

#region Collections
# Processes
Run-ToFile -Command "tasklist.exe" -Args "/v /fo list" -OutFile (Join-Path $outDir "tasklist.txt")
PS-ToFile -ScriptBlock { Get-Process | Sort-Object CPU -Descending | Select-Object Name,Id,CPU,PM,StartTime -ErrorAction SilentlyContinue } -OutFile (Join-Path $outDir "get-process.txt")

# Network basics
Run-ToFile -Command "ipconfig.exe" -Args "/all" -OutFile (Join-Path $outDir "ipconfig_all.txt")
Run-ToFile -Command "arp.exe" -Args "-a" -OutFile (Join-Path $outDir "arp_cache.txt")
# netstat -ab requires admin + can be slow; also gather -ano for PIDs
Run-ToFile -Command "netstat.exe" -Args "-abno" -OutFile (Join-Path $outDir "netstat_abno.txt")
PS-ToFile -ScriptBlock { Get-NetTCPConnection -ErrorAction SilentlyContinue | Sort-Object -Property State,LocalPort } -OutFile (Join-Path $outDir "Get-NetTCPConnection.txt")

# Routing
Run-ToFile -Command "route.exe" -Args "print" -OutFile (Join-Path $outDir "route_print.txt")

# Identity / OS
Run-ToFile -Command "whoami.exe" -Args "/all" -OutFile (Join-Path $outDir "whoami_all.txt")
Run-ToFile -Command "systeminfo.exe" -Args "" -OutFile (Join-Path $outDir "systeminfo.txt")

# DNS resolution
$hostname = $env:COMPUTERNAME
Run-ToFile -Command "nslookup.exe" -Args $hostname -OutFile (Join-Path $outDir "nslookup_self.txt")
Run-ToFile -Command "nslookup.exe" -Args "microsoft.com" -OutFile (Join-Path $outDir "nslookup_microsoft.txt")

# Group Policy results
Run-ToFile -Command "gpresult.exe" -Args "/r /scope user" -OutFile (Join-Path $outDir "gpresult_user.txt")
Run-ToFile -Command "gpresult.exe" -Args "/r /scope computer" -OutFile (Join-Path $outDir "gpresult_computer.txt")

# Users / groups
Run-ToFile -Command "net.exe" -Args "user" -OutFile (Join-Path $outDir "net_user.txt")
Run-ToFile -Command "net.exe" -Args "localgroup administrators" -OutFile (Join-Path $outDir "local_admins.txt")

# Directory listings (keep reasonable)
PS-ToFile -ScriptBlock { Get-ChildItem -Force -ErrorAction SilentlyContinue C:\ | Select-Object Mode,LastWriteTime,Length,Name } -OutFile (Join-Path $outDir "dir_C_root.txt")
PS-ToFile -ScriptBlock { Get-ChildItem -Force -ErrorAction SilentlyContinue $env:USERPROFILE | Select-Object Mode,LastWriteTime,Length,Name } -OutFile (Join-Path $outDir "dir_UserProfile.txt")

# Environment & services (handy for health)
PS-ToFile -ScriptBlock { Get-Service | Sort-Object Status,DisplayName } -OutFile (Join-Path $outDir "services.txt")
PS-ToFile -ScriptBlock { Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue | Select-Object DisplayName,DisplayVersion,Publisher,InstallDate | Sort-Object DisplayName } -OutFile (Join-Path $outDir "installed_software.txt")

# Scheduled tasks (quick view)
PS-ToFile -ScriptBlock { Get-ScheduledTask | Select-Object TaskName,TaskPath,State } -OutFile (Join-Path $outDir "scheduled_tasks.txt")
#endregion

#region Wrap-up: hash + zip
try {
    $hashes = Get-ChildItem $outDir -File | ForEach-Object {
        $h = Get-FileHash $_.FullName -Algorithm SHA256
        [PSCustomObject]@{ File=$_.Name; SHA256=$h.Hash }
    }
    $hashes | Format-Table -AutoSize | Out-String | Out-File -FilePath (Join-Path $outDir "file_hashes_sha256.txt") -Encoding UTF8
} catch { }

Stop-Transcript | Out-Null

try {
    $zipPath = Join-Path $base "$computer`_$ts.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Compress-Archive -Path (Join-Path $outDir '*') -DestinationPath $zipPath -Force
    Write-Host "[*] Archive created: $zipPath"
} catch {
    Write-Warning "Could not create ZIP: $($_.Exception.Message)"
}

# Reveal folder
Invoke-Item $outDir
Write-Host "[*] Done."
#endregion
