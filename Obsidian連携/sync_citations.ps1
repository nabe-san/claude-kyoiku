# rekishi-hp reading-note citations sync
# Pulls the latest src/content/books/*.md from GitHub, then runs
# import_citations.py to reflect the citations into the Obsidian vault.
# Intended to run at Windows logon via Task Scheduler.

$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptDir
$logPath = Join-Path $scriptDir "sync_citations.log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp $Message" | Out-File -FilePath $logPath -Append -Encoding utf8
}

try {
    Set-Location $repoRoot
    $pullOutput = git pull origin main 2>&1 | Out-String
    Write-Log "git pull: $($pullOutput.Trim())"

    Set-Location $scriptDir
    $importOutput = python import_citations.py 2>&1 | Out-String
    Write-Log "import_citations.py: $($importOutput.Trim())"
}
catch {
    Write-Log "error: $($_.Exception.Message)"
}
