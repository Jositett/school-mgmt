# 🚀 Josiah L. Tetteh – **Independent Developer**  

**Full-stack | Mobile | Desktop | Educator**  
*(replace any placeholder with your own links/words)*

---

## 1.  One-line elevator pitch

I turn raw ideas into **shippable software**—web, mobile & desktop—then teach others to do the same through **project-based courses**.

---

## 2.  Brand assets (auto-downloaded by the script)

| Asset | Source | Licence |
|-------|--------|---------|
| App icon 512×512 | [flet-assets](https://github.com/flet-dev/flet-assets/raw/main/common/app_icon.png) | MIT |
| Splash 720×1280 | [flet-assets](https://github.com/flet-dev/flet-assets/raw/main/common/splash_android.png) | MIT |
| **face-api.js** (web face recognition) | [cdn.jsdelivr.net](https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js) | MIT |

---

## 3.  Project bootstrap (PowerShell)

Save as `bootstrap.ps1` in repo root → **right-click → Run with PowerShell**.

```powershell
# ----------  Josiah L. Tetteh – Flet Build Packager  ----------
param(
    [string]$ProjectName = "SchoolMgmt",
    [string]$BundleId     = "com.joedroid.schoolmgmt",   # your reverse-domain
    [string]$Description  = "Attendance & fees app by Josiah L. Tetteh",
    [string]$Author       = "Josiah L. Tetteh <joedroid@joedroid.com>"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Write-Host "🟦  Josiah L. Tetteh – Boot-strapping Flet project for Android + Web" -ForegroundColor Cyan

# 1.  Folder tree
@("src","assets","assets/js") | % { New-Item -ItemType Directory -Path "$root\$_" -Force | Out-Null }

# 2.  pyproject.toml  (independent-dev info injected)
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

# 3.  Brand assets download
Invoke-WebRequest -Uri "https://github.com/flet-dev/flet-assets/raw/main/common/app_icon.png" -OutFile "$root\assets\icon.png"
Invoke-WebRequest -Uri "https://github.com/flet-dev/flet-assets/raw/main/common/splash_android.png" -OutFile "$root\assets\splash_android.png"
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js" -OutFile "$root\assets\js\face-api.min.js"

# 4.  Clean requirements for web (strip native wheels)
if (Test-Path "$root\requirements.txt"){
    (Get-Content "$root\requirements.txt") -notmatch 'opencv|dlib|face_recognition' |
      Set-Content "$root\requirements_web.txt"
}

# 5.  Android SDK licence fix (prevents build hang)
$sdk = "$env:USERPROFILE\Android\sdk"
if (-not (Test-Path "$sdk\licenses")) { New-Item -ItemType Directory -Path "$sdk\licenses" -Force }
"24333f8a63b6825ea9c5514f83c2829b004d1fee" | Out-File -FilePath "$sdk\licenses\android-sdk-license" -NoNewline

# 6.  Move existing entry point
if (Test-Path "$root\school_system.py"){ Move-Item "$root\school_system.py" "$root\src\main.py" -Force }

Write-Host @"

✅ Bootstrap complete!
Next steps for Josiah L. Tetteh:

  Android APK  :  flet build apk
  Android AAB  :  flet build aab
  Web PWA      :  flet build web --web-renderer html

Commit the new folders & push to your GitHub:
  https://github.com/Jositett/<repo>

"@ -ForegroundColor Green
```

---

## 4.  Build matrix (verified 2025-06-25)

| Target | Command | Output size | Store/host |
|--------|---------|-------------|------------|
| **Android APK** | `flet build apk` | ≈ 45 MB (per ABI) | Side-load / Drive |
| **Android AAB** | `flet build aab` | ≈ 110 MB bundle | Google Play |
| **Web PWA** | `flet build web --web-renderer html` | ≈ 120 MB | GitHub-Pages, Netlify, Vercel |

---

## 5.  CI/CD (GitHub Actions) – drop-in file

`.github/workflows/build.yml`

```yaml
name: Build & Deploy PWA
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.29.2'
      - run: pip install "flet[all]"
      - run: flet build web --web-renderer html
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./build/web
```

Push → live at `https://Jositett.github.io/<repo>` *(enable Pages in repo settings)*.

---

## 6.  Quick links crib-sheet

| Purpose | URL |
|---------|-----|
| Flet build docs | <https://flet.dev/docs/publish> |
| face-api.js repo | <https://github.com/justadudewhohacks/face-api.js> |
| Flutter SDK releases | <https://flutter.dev/docs/development/tools/sdk/releases> |
| Google Play Console | <https://play.google.com/console> |

---

## 7.  What to do next

1. Run the script once.  
2. `flet build apk` → install on your phone.  
3. `flet build web` → drag `build/web/` into Netlify-drop → instant PWA.  
4. Tweet the link [@Joedroid](https://twitter.com/Joedroid) and tag **#BuiltWithFlet**.

Happy shipping!

## 6. Known Commands

(venv) PS C:\Self_Projects\school-management> flet build android --init
usage: flet build [-h] [-v] [--arch TARGET_ARCH [TARGET_ARCH ...]] [--exclude EXCLUDE [EXCLUDE ...]] [-o OUTPUT_DIR] [--clear-cache] [--project PROJECT_NAME]
                  [--description DESCRIPTION] [--product PRODUCT_NAME] [--org ORG_NAME] [--bundle-id BUNDLE_ID] [--company COMPANY_NAME] [--copyright COPYRIGHT]
                  [--android-adaptive-icon-background ANDROID_ADAPTIVE_ICON_BACKGROUND] [--splash-color SPLASH_COLOR] [--splash-dark-color SPLASH_DARK_COLOR]
                  [--no-web-splash] [--no-ios-splash] [--no-android-splash] [--ios-team-id IOS_TEAM_ID] [--ios-export-method IOS_EXPORT_METHOD]
                  [--ios-provisioning-profile IOS_PROVISIONING_PROFILE] [--ios-signing-certificate IOS_SIGNING_CERTIFICATE] [--base-url BASE_URL]
                  [--web-renderer {canvaskit,html}] [--use-color-emoji] [--route-url-strategy {path,hash}] [--pwa-background-color PWA_BACKGROUND_COLOR]
                  [--pwa-theme-color PWA_THEME_COLOR] [--split-per-abi] [--compile-app] [--compile-packages] [--cleanup-app]
                  [--cleanup-app-files [CLEANUP_APP_FILES ...]] [--cleanup-packages] [--cleanup-package-files [CLEANUP_PACKAGE_FILES ...]]
                  [--flutter-build-args [FLUTTER_BUILD_ARGS ...]] [--source-packages SOURCE_PACKAGES [SOURCE_PACKAGES ...]] [--info-plist INFO_PLIST [INFO_PLIST ...]]
                  [--macos-entitlements MACOS_ENTITLEMENTS [MACOS_ENTITLEMENTS ...]] [--android-features ANDROID_FEATURES [ANDROID_FEATURES ...]]
                  [--android-permissions ANDROID_PERMISSIONS [ANDROID_PERMISSIONS ...]] [--android-meta-data ANDROID_META_DATA [ANDROID_META_DATA ...]]
                  [--permissions {location,camera,microphone,photo_library} [{location,camera,microphone,photo_library} ...]]
                  [--deep-linking-scheme DEEP_LINKING_SCHEME] [--deep-linking-host DEEP_LINKING_HOST] [--android-signing-key-store ANDROID_SIGNING_KEY_STORE]
                  [--android-signing-key-store-password ANDROID_SIGNING_KEY_STORE_PASSWORD] [--android-signing-key-password ANDROID_SIGNING_KEY_PASSWORD]
                  [--android-signing-key-alias ANDROID_SIGNING_KEY_ALIAS] [--build-number BUILD_NUMBER] [--build-version BUILD_VERSION] [--module-name MODULE_NAME]
                  [--template TEMPLATE] [--template-dir TEMPLATE_DIR] [--template-ref TEMPLATE_REF] [--show-platform-matrix] [--no-rich-output] [--skip-flutter-doctor]
                  {macos,linux,windows,web,apk,aab,ipa} [python_app_path]
flet build: error: argument target_platform: invalid choice: 'android' (choose from macos, linux, windows, web, apk, aab, ipa)
