<#
.SYNOPSIS
    Searches Windows Event Logs for user-specified keywords.

.DESCRIPTION
    eventSearch_keywords.ps1 prompts the analyst to enter one or more keywords,
    a target Windows Event Log (default = Security), and a look-back period (default = 7 days).
    It searches event messages for matching terms and optionally exports results to CSV.

.AUTHOR
    Brian Maroney

.VERSION
    1.0.0

.EXAMPLE
    PS C:\> .\eventSearch_keywords.ps1
    Enter keyword(s) to search (separate multiple with commas): powershell, cmd.exe
    Enter log name to search (default = Security): System
    Enter number of days to look back (default = 7): 14

.NOTES
    • Run PowerShell as Administrator for full access to Security logs.
    • Adjust MaxEvents for performance on large systems.
#>

# Prompt user for keywords
$keywords = Read-Host "Enter keyword(s) to search (separate multiple with commas)"
$keywordList = $keywords -split ',' | ForEach-Object { $_.Trim() }

if ($keywordList.Count -eq 0 -or [string]::IsNullOrWhiteSpace($keywordList[0])) {
    Write-Host "[!] No keywords entered. Exiting." -ForegroundColor Red
    exit 1
}

# Prompt user for log name (default = Security)
$logChoice = Read-Host "Enter log name to search (default = Security). Examples: Security, System, Application"
if ([string]::IsNullOrWhiteSpace($logChoice)) {
    $logChoice = "Security"
}

# Prompt for time range (default = 7 days)
$days = Read-Host "Enter number of days to look back (default = 7)"
if (-not [int]::TryParse($days, [ref]$null)) {
    $days = 7
}
$startTime = (Get-Date).AddDays(-[int]$days)

Write-Host "`n[+] Searching '$logChoice' log for keywords from the past $days days...`n"

# Retrieve events
try {
    # Limit retrieval to improve performance (can be tuned)
    $events = Get-WinEvent -LogName $logChoice -ErrorAction Stop |
        Where-Object { $_.TimeCreated -ge $startTime }
} catch {
    Write-Host "[!] Error reading log '$logChoice': $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Initialize result container
$matches = @()

# Iterate through each keyword
foreach ($keyword in $keywordList) {
    Write-Host "Searching for keyword: '$keyword'..."
    $found = $events | Where-Object { $_.Message -match [regex]::Escape($keyword) }

    if ($found) {
        Write-Host "  -> Found $($found.Count) matching events for '$keyword'." -ForegroundColor Cyan
        $matches += $found
    } else {
        Write-Host "  -> No matches for '$keyword'." -ForegroundColor Yellow
    }
}

# Display and optionally export
if ($matches.Count -gt 0) {
    Write-Host "`n[+] Total matching events: $($matches.Count)`n"
    $matches | Select-Object TimeCreated, Id, LevelDisplayName, ProviderName, Message |
        Format-Table -AutoSize

    # Export option
    $export = Read-Host "`nDo you want to export results to CSV? (Y/N)"
    if ($export -match '^[Yy]') {
        $outFile = "EventLog_SearchResults_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"
        $matches | Select-Object TimeCreated, Id, LevelDisplayName, ProviderName, Message |
            Export-Csv -NoTypeInformation -Path $outFile
        Write-Host "[+] Results exported to $outFile"
    }
} else {
    Write-Host "`n[!] No matching events found." -ForegroundColor Yellow
}

Write-Host "`nSearch complete.`n"
