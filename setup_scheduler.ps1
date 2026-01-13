# PowerShell script to set up Windows Task Scheduler

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectDir "venv\Scripts\python.exe"
$MainScript = Join-Path $ProjectDir "src\main.py"
$LogDir = Join-Path $ProjectDir "logs"

# Check if virtual environment exists
if (-not (Test-Path $PythonExe)) {
    Write-Host "Error: Python virtual environment not found at $ProjectDir\venv" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv; .\venv\Scripts\activate; pip install -r requirements.txt"
    exit 1
}

Write-Host "Canvas Scraper - Scheduler Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will create a scheduled task to run the scraper daily at 12:00 PM (noon)"
Write-Host ""

$action = New-ScheduledTaskAction -Execute $PythonExe `
    -Argument $MainScript `
    -WorkingDirectory $ProjectDir

$trigger = New-ScheduledTaskTrigger -Daily -At 12:00PM

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable

$task = New-ScheduledTask -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description "Canvas file scraper - runs daily at noon"

$confirm = Read-Host "Register this scheduled task? [y/n]"

if ($confirm -eq "y" -or $confirm -eq "Y") {
    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName "CanvasScraper" -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName "CanvasScraper" -Confirm:$false
    }
    
    # Register new task
    Register-ScheduledTask -TaskName "CanvasScraper" -InputObject $task
    
    Write-Host ""
    Write-Host "✓ Scheduled task registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The scraper will run daily at 12:00 PM"
    Write-Host ""
    Write-Host "Useful commands:"
    Write-Host "  View task: Get-ScheduledTask -TaskName CanvasScraper"
    Write-Host "  Run now: Start-ScheduledTask -TaskName CanvasScraper"
    Write-Host "  Remove: Unregister-ScheduledTask -TaskName CanvasScraper"
    Write-Host "  View logs: Get-Content $LogDir\scraper.log -Tail 50"
} else {
    Write-Host ""
    Write-Host "Scheduled task not registered."
}
