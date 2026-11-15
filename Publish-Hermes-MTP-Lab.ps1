# Publish the complete checked source tree without manual file edits.
# Never force-push, rewrite history, touch local Hermes, or require a .git in the ZIP.
$ErrorActionPreference = 'Stop'
$repository = 'https://github.com/SergPoletaev/Hermes-MTP-Lab.git'
$branch = 'main'
$source = $PSScriptRoot
$workspace = $null
$published = $false
try {
    Write-Host 'Hermes MTP Lab v0.3.3 - publish complete source repository' -ForegroundColor Cyan
    foreach ($required in @('plugin.yaml', 'README.md', '.github\workflows\ci.yml', 'requirements-ci.txt',
                           'desktop\plugin.js', 'dashboard\plugin_api.py', 'tests\test_companion_api.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $source $required) -PathType Leaf)) {
            throw "The extracted repository is incomplete: $required"
        }
    }
    $gitCmd = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($gitCmd) {
        $git = $gitCmd.Source
    } else {
        $desktopRoot = Join-Path $env:LOCALAPPDATA 'GitHubDesktop'
        $bundled = @(Get-ChildItem -Path $desktopRoot -Directory -Filter 'app-*' -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending | ForEach-Object {
                Join-Path $_.FullName 'resources\app\git\cmd\git.exe'
            } | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
        if (-not $bundled.Count) {
            throw 'Git not found. Install Git or GitHub Desktop, sign in to GitHub, and run this script again.'
        }
        $git = $bundled[0]
    }
    $workspace = Join-Path ([IO.Path]::GetTempPath()) ('HermesMTPPublish-' + [guid]::NewGuid().ToString('N'))
    Write-Host 'Cloning current main branch; preserving Git history...'
    & $git clone --quiet --branch $branch --single-branch $repository $workspace
    if ($LASTEXITCODE -ne 0) { throw 'Clone failed. Check GitHub authentication and network access.' }

    # The public repository v0.3.0 stored the plugin in this obsolete nested directory.
    # Remove only this known legacy path; preserve all unrelated remote content.
    & $git -C $workspace rm --quiet -r --ignore-unmatch -- hermes-mtp-lab
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove obsolete nested plugin path.' }

    $skipDirs = @('.git', 'dist', 'build', '__pycache__', '.pytest_cache', '.idea', '.vscode', 'node_modules')
    foreach ($file in (Get-ChildItem -LiteralPath $source -File -Recurse -Force)) {
        $rel = $file.FullName.Substring($source.Length).TrimStart([char[]]@('\', '/'))
        $parts = $rel -split '[\\/]'
        if (@($parts | Where-Object { $skipDirs -contains $_ }).Count) { continue }
        if ($file.Extension -in @('.zip', '.pyc', '.pyo', '.log', '.tmp')) { continue }
        if ($file.Name -like '.mtp-lab-pending*') { continue }
        $destination = Join-Path $workspace $rel
        $parent = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    }
    & $git -C $workspace add --all
    if ($LASTEXITCODE -ne 0) { throw 'Could not stage the complete repository.' }
    & $git -C $workspace diff --cached --check
    if ($LASTEXITCODE -ne 0) { throw 'Git detected whitespace errors in the staged changes.' }
    & $git -C $workspace diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'No changes: GitHub main already contains these repository files.' -ForegroundColor Green
        $published = $true
    } elseif ($LASTEXITCODE -eq 1) {
        $name = (& $git -C $workspace log -1 --format='%an').Trim()
        $email = (& $git -C $workspace log -1 --format='%ae').Trim()
        if (-not $name -or -not $email) { throw 'Could not determine existing repository commit identity.' }
        Write-Host 'Committing and pushing all checked project files; no force push...'
        & $git -C $workspace -c "user.name=$name" -c "user.email=$email" commit -m 'Release Hermes MTP Lab v0.3.3 complete verified repository'
        if ($LASTEXITCODE -ne 0) { throw 'Git commit failed.' }
        & $git -C $workspace push origin "HEAD:$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Push failed. No force push was attempted; repository may need GitHub authentication.' }
        $published = $true
        Write-Host 'SUCCESS: complete source pushed to GitHub main. GitHub Actions will run automatically.' -ForegroundColor Green
    } else {
        throw 'Could not inspect staged changes.'
    }
    Write-Host $repository
} catch {
    Write-Host ('PUBLISH FAILED: ' + $_.Exception.Message) -ForegroundColor Red
    if ($workspace -and (Test-Path -LiteralPath $workspace)) {
        Write-Host "Temporary clone kept for diagnostics: $workspace" -ForegroundColor Yellow
    }
    exit 1
} finally {
    if ($published -and $workspace -and (Test-Path -LiteralPath $workspace)) {
        Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue
    }
}
exit 0
