$ErrorActionPreference = 'Stop'
$script:Result = 1
try {
    $pluginName = 'hermes-mtp-lab'
    $source = $PSScriptRoot
    $hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    $target = Join-Path (Join-Path $hermesRoot 'plugins') $pluginName
    $shim = Join-Path (Join-Path $hermesRoot 'bin') 'hermes.cmd'
    $config = Join-Path $hermesRoot 'config.yaml'
    $timeStamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $suffix = $timeStamp + '-' + ([guid]::NewGuid().ToString('N').Substring(0,8))

    Write-Host 'Hermes MTP Lab v0.4.0 - Installer (native Hermes plugin enable)' -ForegroundColor Cyan
    Write-Host "Source: $source"
    Write-Host "Destination: $target"

    foreach($file in @('plugin.yaml','__init__.py','desktop\plugin.js','dashboard\plugin_api.py','dashboard\bench_core.py','dashboard\model_support.py','dashboard\quality_eval.py','dashboard\hardware_diag.py','dashboard\manifest.json','data\benchmark_scene.jpg')) {
        if (-not (Test-Path -LiteralPath (Join-Path $source $file) -PathType Leaf)) {
            throw "Plugin source is incomplete: $file. Extract entire ZIP before running."
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $hermesRoot 'hermes-agent') -PathType Container)) {
        throw 'Hermes agent directory is missing: refusing to install to an unrecognized home.'
    }
    if (-not (Test-Path -LiteralPath $shim -PathType Leaf)) {
        throw "Hermes launcher is missing: $shim. No plugin files or settings have been modified."
    }
    if (Get-Process -Name Hermes -ErrorAction SilentlyContinue) {
        throw 'Hermes.exe is running. Fully Quit from the tray and run installer again.'
    }

    # The installer must never parse, append or rewrite arbitrary user YAML.
    # Hermes CLI is responsible for all plugin consent and config edits.
    $choice = Read-Host 'Install and enable ONLY hermes-mtp-lab using Hermes built-in command? [Y/n]'
    if ($choice -and $choice -notmatch '^(?i:y|yes|д|да)$') {
        Write-Host 'Cancelled. No files changed.' -ForegroundColor Yellow
        $script:Result = 0
    } else {
        $parent = Split-Path -Parent $target
        New-Item -Path $parent -ItemType Directory -Force | Out-Null
        $stage = Join-Path $parent ('.mtp-lab-stage-' + $suffix)
        $backupRoot = Join-Path $hermesRoot 'plugin-backups'
        New-Item -Path $backupRoot -ItemType Directory -Force | Out-Null
        $backup = Join-Path $backupRoot ($pluginName + '.backup-' + $suffix)
        $cfgBackup = $null
        $hadExisting = Test-Path -LiteralPath $target -PathType Container
        $movedExisting = $false
        $installed = $false
        try {
            New-Item -Path $stage -ItemType Directory -Force | Out-Null
            # Install only the plugin package, not .git, CI, test files, or repository docs.
            foreach($file in @('plugin.yaml','__init__.py')) {
                Copy-Item -LiteralPath (Join-Path $source $file) -Destination (Join-Path $stage $file) -Force
            }
            foreach($folder in @('desktop','dashboard','data')) {
                Copy-Item -LiteralPath (Join-Path $source $folder) -Destination $stage -Recurse -Force
            }
            foreach($file in @('plugin.yaml','__init__.py','desktop\plugin.js','dashboard\plugin_api.py','dashboard\bench_core.py','dashboard\model_support.py','dashboard\quality_eval.py','dashboard\hardware_diag.py','dashboard\manifest.json','data\benchmark_scene.jpg')) {
                if (-not (Test-Path -LiteralPath (Join-Path $stage $file) -PathType Leaf)) {throw "Staging check failed: $file"}
            }
            if (Test-Path -LiteralPath $config -PathType Leaf) {
                $cfgBackup = "$config.mtp-lab-before-$suffix"
                Copy-Item -LiteralPath $config -Destination $cfgBackup -Force
                Write-Host "Config safety backup: $cfgBackup"
            }
            if ($hadExisting) {
                Move-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
                $movedExisting = $true
                Write-Host "Previous plugin backed up: $backup"
            }
            Move-Item -LiteralPath $stage -Destination $target -ErrorAction Stop
            $installed = $true
            Write-Host 'Plugin files: installed.' -ForegroundColor Green
            Write-Host 'Enabling Python backend via OFFICIAL Hermes CLI (not a custom YAML editor)...' -ForegroundColor Cyan
            & $shim plugins enable $pluginName
            if ($LASTEXITCODE -ne 0) {
                throw "Hermes CLI refused to enable $pluginName (exit code $LASTEXITCODE)."
            }
            Write-Host 'SUCCESS: Hermes CLI enabled the plugin.' -ForegroundColor Green
            Write-Host 'Fully restart Hermes, then enable the Desktop card if necessary and open MTP Lab.'
            $script:Result = 0
        } catch {
            Write-Host ('INSTALL FAILED: '+$_.Exception.Message) -ForegroundColor Red
            Write-Host 'Restoring the previous plugin files (if any)...' -ForegroundColor Yellow
            if ($installed -and (Test-Path -LiteralPath $target)) {
                $failedPath = Join-Path $backupRoot ($pluginName+'.failed-'+$suffix)
                Move-Item -LiteralPath $target -Destination $failedPath -ErrorAction Stop
                Write-Host "Failed version kept for inspection: $failedPath"
            }
            if ($movedExisting -and (Test-Path -LiteralPath $backup)) {
                Move-Item -LiteralPath $backup -Destination $target -ErrorAction Stop
                Write-Host 'Previous plugin restored.'
            }
            # If Hermes CLI returned failure after changing config, preserve backup for manual review.
            # Never overwrite config.yaml on a guess; the official command owns it.
            if ($cfgBackup) {Write-Host "Original config backup is available: $cfgBackup"}
            Write-Host 'No MTP model configuration, lifecycle files or ChatVault were modified by this installer.'
            $script:Result = 1
        } finally {
            if (Test-Path -LiteralPath $stage) {Remove-Item -LiteralPath $stage -Recurse -Force}
        }
    }
} catch {
    Write-Host ('ERROR: '+$_.Exception.Message) -ForegroundColor Red
    $script:Result = 1
}
exit $script:Result
