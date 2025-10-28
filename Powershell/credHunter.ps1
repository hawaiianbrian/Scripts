<#
credHunter.ps1
Search for files (filenames or contents) containing credential-related keywords.
Supports text, PDF, and Microsoft Office files.

If "pdftotext.exe" exists in PATH, PDF content will be parsed.
Office OpenXML formats (.docx/.xlsx/.pptx) are parsed internally.
All other files are skipped from content scan if unsupported.

Usage examples:
  .\credHunter.ps1 -Path "C:\Users" -OutputCsv "C:\Temp\credhunt.csv"
  .\credHunter.ps1 -Path "C:\Users" -CheckContents -OutputCsv "C:\Temp\credhunt_full.csv"
#>

param(
    [string]$Path = "C:\Users",
    [string]$OutputCsv = (Join-Path $env:TEMP 'credhunt_results.csv'),
    [switch]$CheckContents = $false,
    [int]$MaxFileSizeMB = 50
)

# Keyword patterns
$tokens = @('password','pw\b','pwd\b','account','user\b','username','creds','credentials')
$regex = '(?i)(' + ($tokens -join '|') + ')'

# Extensions
$SearchExtensions = @(
    '.txt','.log','.csv','.env','.json','.xml','.yaml','.yml','.ini','.md',
    '.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.rtf'
)

# Which ones we can read as text internally
$TextContentExtensions = @('.txt','.log','.csv','.env','.json','.xml','.yaml','.yml','.ini','.md','.ps1','.bat','.cmd')

# Check for external PDF tool
$PdfTool = (Get-Command "pdftotext.exe" -ErrorAction SilentlyContinue)
if ($PdfTool) {
    Write-Host "PDF text extraction available via $($PdfTool.Source)"
} else {
    Write-Host "pdftotext.exe not found — PDFs will be skipped for content scan."
}

$maxBytes = [int64]($MaxFileSizeMB * 1MB)
$results = [System.Collections.Generic.List[object]]::new()

# Helper to read small plain-text files
function Try-ReadText([string]$file) {
    try {
        $fi = Get-Item -LiteralPath $file -ErrorAction Stop
        if ($fi.Length -gt $maxBytes) { return $null }
        return Get-Content -LiteralPath $file -Raw -ErrorAction Stop -Encoding UTF8
    } catch { return $null }
}

# Extract text from PDF via pdftotext.exe (if available)
function Try-ExtractPdfText([string]$file) {
    if (-not $PdfTool) { return $null }
    try {
        $tempOut = [System.IO.Path]::GetTempFileName()
        & $PdfTool.Source -nopgbrk -q -enc UTF-8 "$file" "$tempOut" 2>$null
        if (Test-Path $tempOut) {
            $text = Get-Content -Path $tempOut -Raw -ErrorAction SilentlyContinue
            Remove-Item $tempOut -Force -ErrorAction SilentlyContinue
            return $text
        }
    } catch { return $null }
    return $null
}

# Extract text from Office OpenXML (docx/xlsx/pptx)
function Try-ExtractOfficeText([string]$file) {
    try {
        $tempDir = Join-Path $env:TEMP ("credhunter_" + [System.IO.Path]::GetFileNameWithoutExtension($file))
        if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue }
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($file, $tempDir)
        $xmlFiles = Get-ChildItem -Path $tempDir -Filter *.xml -Recurse -ErrorAction SilentlyContinue
        $combined = ""
        foreach ($xml in $xmlFiles) {
            $combined += (Get-Content -Path $xml.FullName -Raw -ErrorAction SilentlyContinue)
        }
        Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        return $combined
    } catch {
        return $null
    }
}

# Main enumeration
Write-Host "Starting scan for credential terms in filenames (and optionally contents)..."
$files = Get-ChildItem -Path $Path -Recurse -Force -File -ErrorAction SilentlyContinue |
         Where-Object { $SearchExtensions -contains ([System.IO.Path]::GetExtension($_.FullName).ToLower()) }

foreach ($f in $files) {
    $ext = [System.IO.Path]::GetExtension($f.FullName).ToLower()
    $matched = $false

    # Filename match
    if ($f.Name -match $regex) {
        $results.Add([pscustomobject]@{
            FullName = $f.FullName
            Name = $f.Name
            Extension = $ext
            MatchType = 'Filename'
            ContentSample = $null
            LastWriteTime = $f.LastWriteTime
        })
        $matched = $true
    }

    # Optional content scanning
    if ($CheckContents) {
        $text = $null
        if ($TextContentExtensions -contains $ext) {
            $text = Try-ReadText $f.FullName
        } elseif ($ext -eq '.pdf') {
            $text = Try-ExtractPdfText $f.FullName
        } elseif ($ext -in @('.docx','.xlsx','.pptx')) {
            $text = Try-ExtractOfficeText $f.FullName
        }

        if ($text -and $text -match $regex) {
            $lines = $text -split "`r?`n"
            $samples = @()
            for ($i=0; $i -lt $lines.Length; $i++) {
                if ($lines[$i] -match $regex) {
                    $samples += $lines[$i].Trim()
                    if ($samples.Count -ge 3) { break }
                }
            }
            $results.Add([pscustomobject]@{
                FullName = $f.FullName
                Name = $f.Name
                Extension = $ext
                MatchType = 'Content'
                ContentSample = ($samples -join " | ")
                LastWriteTime = $f.LastWriteTime
            })
        }
    }
}

# Output
if ($results.Count -gt 0) {
    $results | Export-Csv -Path $OutputCsv -NoTypeInformation -Encoding UTF8 -Force
    Write-Host "`nScan complete — $($results.Count) matches found."
    Write-Host "Results saved to: $OutputCsv"
} else {
    Write-Host "`nScan complete — no matches found."
}
