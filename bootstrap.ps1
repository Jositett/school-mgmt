#requires -Version 5.1
<#
.SYNOPSIS
  Joedroid – Flet Build Packager (GitHub-ready, offline-safe)
  Creates Android APK / AAB + Web PWA skeleton in one click.
#>
param(
    [string]$ProjectName = "SchoolMgmt",
    [string]$BundleId     = "com.joedroid.schoolmgmt",
    [string]$Description  = "Attendance & fees app by Joedroid",
    [string]$Author       = "Josiah L. Tetteh <joedroid@joedroid.com>",
    [string]$RepoName     = "school-mgmt",   # GitHub repo name (optional)
    [switch]$SkipGitHub   = $false           # set if you only want local files
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Write-Host "🟦  Joedroid – Boot-strapping Flet project for Android + Web" -ForegroundColor Cyan

# 1.  Folder tree
@("src","assets","assets/js",".github/workflows") | % {
    New-Item -ItemType Directory -Path "$root\$_" -Force | Out-Null
}

# 2.  pyproject.toml (Joedroid branding)
@"
[project]
name    = "$ProjectName"
version = "1.0.0"
description = "$Description"
authors = ["$Author"]

[tool.flet]
org  = "$($BundleId.Split('.')[0..1] -join '.')"
product = "$ProjectName"
company = "Joedroid"
copyright = "© 2025 Joedroid"

[tool.flet.app]
path = "src"

[tool.flet.android]
package = "$BundleId"
split_per_abi = true
permissions = ["CAMERA","INTERNET"]

[tool.flet.web]
renderer = "html"
"@ | Out-File -FilePath "$root\pyproject.toml" -Encoding utf8

# 3.  Download helper (cross-PowerShell)
function Get-JoedroidAsset {
    param([string]$Url,[string]$OutFile,[string]$FallbackUrl)
    try   { Invoke-WebRequest -Uri $Url -OutFile $OutFile -ErrorAction Stop }
    catch {
        Write-Host "⚠️  $Url failed – trying fallback …" -ForegroundColor Yellow
        try   { Invoke-WebRequest -Uri $FallbackUrl -OutFile $OutFile -ErrorAction Stop }
        catch {
            Write-Host "⚠️  Fallback also failed – creating blank placeholder" -ForegroundColor Yellow
            [IO.File]::WriteAllBytes($OutFile, [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="))
        }
    }
}

# 4.  Real, stable downloads (searched & verified)
$iconUrl      = "https://cdn-icons-png.flaticon.com/512/2920/2920277.png"
$iconFallback = "https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Color/App Icon/App Icon color.png"

$splashUrl      = "https://images.unsplash.com/photo-1557683316-973673baf926?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=720&q=80"
$splashFallback = "https://raw.githubusercontent.com/flet-dev/flet-assets/main/common/splash_android.png"

$jsUrl      = "https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js"
$jsFallback = "https://unpkg.com/face-api.js@0.22.2/dist/face-api.min.js"

Get-JoedroidAsset -Url $iconUrl -OutFile "$root\assets\icon.png" -FallbackUrl $iconFallback
Get-JoedroidAsset -Url $splashUrl -OutFile "$root\assets\splash_android.png" -FallbackUrl $splashFallback
Get-JoedroidAsset -Url $jsUrl -OutFile "$root\assets\js\face-api.min.js" -FallbackUrl $jsFallback

# 5.  Clean requirements for web (strip native wheels)
if (Test-Path "$root\requirements.txt"){
    (Get-Content "$root\requirements.txt") -notmatch 'opencv|dlib|face_recognition' | Set-Content "$root\requirements_web.txt"
}

# 6.  Android SDK licence fix
$sdk = "$env:USERPROFILE\Android\sdk"
if (-not (Test-Path "$sdk\licenses")) { New-Item -ItemType Directory -Path "$sdk\licenses" -Force }
"24333f8a63b6825ea9c5514f83c2829b004d1fee" | Out-File -FilePath "$sdk\licenses\android-sdk-license" -NoNewline

# 7.  Move main entry point
if (Test-Path "$root\school_system.py"){ Move-Item "$root\school_system.py" "$root\src\main.py" -Force }

# 8.  GitHub Actions workflow (build APK + Web PWA on push)
@'
name: Build Joedroid App
on:
  push:
    branches: [main]

jobs:
  build-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.29.2'
      - run: pip install "flet[all]"
      - run: flet build web --web-renderer html --release
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./build/web

  build-apk:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.29.2'
      - run: pip install "flet[all]"
      - run: flet build apk --release
      - uses: actions/upload-artifact@v4
        with:
          name: joedroid-apk
          path: build/android/gradle/app/build/outputs/apk/release/app-release.apk
'@ | Out-File -FilePath "$root\.github\workflows\build.yml" -Encoding utf8

# 9.  Optional: create & push GitHub repo
if (-not $SkipGitHub) {
    try {
        Write-Host "🐙  Creating GitHub repo '$RepoName' …" -ForegroundColor Cyan
        gh repo create $RepoName --public --description $Description --source=. --remote=origin --push
        Write-Host "✅  Repo ready: https://github.com/Jositett/$RepoName" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  GitHub CLI failed – skipping remote create" -ForegroundColor Yellow
    }
}

Write-Host @"

✅ Joedroid bootstrap complete!
Next steps:

  Android APK  :  flet build apk
  Android AAB  :  flet build aab
  Web PWA      :  flet build web --web-renderer html

Live site (after push):
  https://Jositett.github.io/$RepoName

"@ -ForegroundColor Green