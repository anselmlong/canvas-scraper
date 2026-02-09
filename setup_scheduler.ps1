# PowerShell script to set up Windows Task Scheduler
# Works for both native Windows and WSL environments

param(
    [switch]$Uninstall,
    [switch]$RunNow,
    [string]$Trigger = "login"  # "login", "startup", or "daily"
)

$TaskName = "CanvasScraper"

# Uninstall mode
if ($Uninstall) {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Scheduled task '$TaskName' removed successfully." -ForegroundColor Green
    } else {
        Write-Host "No scheduled task named '$TaskName' found." -ForegroundColor Yellow
    }
    exit 0
}

# Run now mode
if ($RunNow) {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Task started. Check logs for output." -ForegroundColor Green
    } else {
        Write-Host "No scheduled task named '$TaskName' found. Run setup first." -ForegroundColor Red
    }
    exit 0
}

# Detect environment
function Test-IsWSL {
    # Check if we're being called from WSL context
    $wslDistros = wsl --list --quiet 2>$null
    return $LASTEXITCODE -eq 0 -and $wslDistros
}

function Get-WSLUsername {
    $result = wsl whoami 2>$null
    if ($LASTEXITCODE -eq 0) {
        return $result.Trim()
    }
    return $null
}

function Get-WSLProjectPath {
    param([string]$WindowsPath)

    # Convert Windows path to WSL path
    $result = wsl wslpath -u "$WindowsPath" 2>$null
    if ($LASTEXITCODE -eq 0) {
        return $result.Trim()
    }

    # Fallback: manual conversion
    if ($WindowsPath -match '^([A-Za-z]):\\(.*)$') {
        $drive = $matches[1].ToLower()
        $path = $matches[2] -replace '\\', '/'
        return "/mnt/$drive/$path"
    }
    return $null
}

# Get script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "Canvas Scraper - Scheduler Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Detect if project is in WSL filesystem or Windows filesystem
$IsWSLPath = $ScriptDir -match '^\\\\wsl'
$HasWSL = Test-IsWSL

if ($IsWSLPath -or (-not (Test-Path "$ScriptDir\venv\Scripts\python.exe"))) {
    # Project is in WSL or no Windows venv found - use WSL mode
    Write-Host "Detected: Project in WSL environment" -ForegroundColor Yellow
    Write-Host ""

    if (-not $HasWSL) {
        Write-Host "Error: WSL is not installed or not running." -ForegroundColor Red
        exit 1
    }

    $WslUsername = Get-WSLUsername
    if (-not $WslUsername) {
        Write-Host "Error: Could not detect WSL username." -ForegroundColor Red
        exit 1
    }

    # Get project path in WSL format
    $WslProjectPath = wsl pwd 2>$null
    if (-not $WslProjectPath -or $LASTEXITCODE -ne 0) {
        # Try to find the project path
        $WslProjectPath = wsl wslpath -u "'$ScriptDir'" 2>$null
        if (-not $WslProjectPath) {
            Write-Host "Error: Could not determine WSL project path." -ForegroundColor Red
            Write-Host "Please run this script from within the project directory in WSL:" -ForegroundColor Yellow
            Write-Host "  cd /path/to/canvas-scraper && powershell.exe ./setup_scheduler.ps1" -ForegroundColor Yellow
            exit 1
        }
    }
    $WslProjectPath = $WslProjectPath.Trim()

    Write-Host "WSL Username: $WslUsername" -ForegroundColor Gray
    Write-Host "Project Path: $WslProjectPath" -ForegroundColor Gray
    Write-Host ""

    # Build WSL command using timeout wrapper for graceful shutdown support
    $WslCommand = "cd '$WslProjectPath' && bash run_with_timeout.sh"

    $action = New-ScheduledTaskAction -Execute "wsl.exe" `
        -Argument "-u $WslUsername -- bash -c `"$WslCommand`""

    $ExecuteInfo = "wsl.exe -u $WslUsername -- bash -c `"$WslCommand`""

} else {
    # Native Windows mode
    Write-Host "Detected: Native Windows environment" -ForegroundColor Yellow
    Write-Host ""

    $PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"
    $MainScript = Join-Path $ScriptDir "src\main.py"

    if (-not (Test-Path $PythonExe)) {
        Write-Host "Error: Python virtual environment not found at $ScriptDir\venv" -ForegroundColor Red
        Write-Host "Please run: python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt"
        exit 1
    }

    $action = New-ScheduledTaskAction -Execute $PythonExe `
        -Argument "`"$MainScript`"" `
        -WorkingDirectory $ScriptDir

    $ExecuteInfo = "$PythonExe `"$MainScript`""
}

# Create trigger based on parameter
switch ($Trigger.ToLower()) {
    "login" {
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $TriggerDesc = "at user login"
    }
    "startup" {
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $TriggerDesc = "at system startup"
    }
    "daily" {
        $trigger = New-ScheduledTaskTrigger -Daily -At 5:00PM
        $TriggerDesc = "daily at 5:00 PM"
    }
    default {
        Write-Host "Invalid trigger type. Use: login, startup, or daily" -ForegroundColor Red
        exit 1
    }
}

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

$task = New-ScheduledTask -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description "Canvas file scraper - syncs files from Canvas LMS"

Write-Host "Task Configuration:" -ForegroundColor White
Write-Host "  Name: $TaskName"
Write-Host "  Trigger: $TriggerDesc"
Write-Host "  Execute: $ExecuteInfo"
Write-Host ""

$confirm = Read-Host "Register this scheduled task? [y/n]"

if ($confirm -eq "y" -or $confirm -eq "Y") {
    # Remove existing task if present
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Removing existing task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # Register new task
    Register-ScheduledTask -TaskName $TaskName -InputObject $task | Out-Null

    Write-Host ""
    Write-Host "Scheduled task registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The scraper will run $TriggerDesc"
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Cyan
    Write-Host "  Run now:    .\setup_scheduler.ps1 -RunNow"
    Write-Host "  Uninstall:  .\setup_scheduler.ps1 -Uninstall"
    Write-Host "  View task:  Get-ScheduledTask -TaskName $TaskName"
    Write-Host "  View logs:  Get-Content logs\scraper.log -Tail 50"
} else {
    Write-Host ""
    Write-Host "Setup cancelled."
}
