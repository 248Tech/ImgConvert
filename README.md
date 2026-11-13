<div align="center">

<img src="site/assets/icon-192.png" alt="ImgConvert logo" width="96" height="96">

# ImgConvert

**Free, offline image converter for Windows — HEIC to JPG, PNG, WebP, GIF and TIFF in one click.**
No ads · No telemetry · No installer · Open source

[![Download](https://img.shields.io/badge/⬇_Download-Windows_.exe-4f8cff?style=for-the-badge)](https://github.com/248Tech/ImgConvert/releases/latest)
[![Live Demo](https://img.shields.io/badge/▶_Try_in_browser-online_demo-22c55e?style=for-the-badge)](https://248tech.github.io/ImgConvert/demo/)

[![License: MIT](https://img.shields.io/github/license/248Tech/ImgConvert?style=flat-square&color=4f8cff)](LICENSE)
[![Release](https://img.shields.io/github/v/release/248Tech/ImgConvert?style=flat-square&color=4f8cff)](https://github.com/248Tech/ImgConvert/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/248Tech/ImgConvert/total?style=flat-square&color=22c55e)](https://github.com/248Tech/ImgConvert/releases)
[![Stars](https://img.shields.io/github/stars/248Tech/ImgConvert?style=flat-square&color=f59e0b)](https://github.com/248Tech/ImgConvert/stargazers)
[![Last commit](https://img.shields.io/github/last-commit/248Tech/ImgConvert?style=flat-square&color=4f8cff)](https://github.com/248Tech/ImgConvert/commits/master)
[![Issues](https://img.shields.io/github/issues/248Tech/ImgConvert?style=flat-square)](https://github.com/248Tech/ImgConvert/issues)
![Platform: Windows](https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Offline](https://img.shields.io/badge/100%25-offline-22c55e?style=flat-square)
![No telemetry](https://img.shields.io/badge/telemetry-none-22c55e?style=flat-square)

[**Website**](https://248tech.github.io/ImgConvert/) · [**Online demo**](https://248tech.github.io/ImgConvert/demo/) · [Download](https://github.com/248Tech/ImgConvert/releases/latest) · [Report a bug](https://github.com/248Tech/ImgConvert/issues)

<img src="assets/screenshot.png" alt="ImgConvert screenshot" width="420">

</div>

> **Try it before you download:** the [online demo](https://248tech.github.io/ImgConvert/demo/) converts JPEG, PNG and WebP right in your browser — your files never leave your device. The Windows app adds HEIC, GIF and TIFF, folders and the Explorer right-click menu.

## About ImgConvert

**Keywords:** image converter, HEIC to JPG, batch image converter, offline image converter for Windows, WebP converter, PNG to JPG, TIFF converter, portable, privacy-friendly.


ImgConvert batch-converts images between JPEG/JPG, PNG, WebP, GIF, TIFF/TIF, and HEIC/HEIF. It was built around a simple idea: a tool this small shouldn't come with an installer, an account, a subscription, or a network connection.

- **Lightweight** — a single portable `.exe` (~21 MB), no installer, no admin rights, no dependencies to set up.
- **Open source** — MIT licensed. Read every line, fork it, change it.
- **Ad-free** — no ads, no upsells, no "Pro" tier.
- **Doesn't phone home** — no telemetry, no analytics, no update-checker pinging a server. It never makes a network request. Your images stay on your machine.

## Features

- Batch convert between JPEG/JPG, PNG, WebP, GIF, TIFF/TIF, and HEIC/HEIF
- Drag and drop files or folders, or paste a path directly
- Windows Explorer right-click **Convert To** menu, per format, output next to the original file
- Automatic EXIF-orientation correction (fixes sideways/upside-down phone photos)
- Progress bar and a per-file success/failure log
- Light and dark theme toggle
- Code-signed executable

## Download

Grab the latest Windows exe from the [Releases](https://github.com/248Tech/ImgConvert/releases/latest) page — no Python install needed.

> **winget:** a winget package is not available yet (the first submission was closed without being merged). Until it is, download the `.exe` from [Releases](https://github.com/248Tech/ImgConvert/releases/latest).

## Running from source

```
pip install -r requirements.txt
python imgconvert.py
```

`tkinterdnd2` is optional — if it's missing, the app still works, you just use the "Add Files…" / "Add Folder…" buttons instead of drag-and-drop.

## Usage

1. Drag files/folders onto the window, click "Add Files…" / "Add Folder…", or paste a path directly.
2. Pick the target format from the dropdown.
3. Pick an output folder (defaults to a `converted/` subfolder next to the first file).
4. Click **Convert**.

Files that fail to convert (not an image, corrupt, etc.) are skipped and listed in the log — the rest of the batch still runs.

## Right-click "Convert To" menu

Click **"Add Right-Click Menu"** in the app's header to add a **Convert To** submenu (JPEG, PNG, WebP, GIF, HEIC, TIFF) to the Explorer right-click menu for supported image files. Pick a format and the converted file is written right next to the original — no need to open the app.

This writes only to `HKEY_CURRENT_USER`, so it applies to your Windows account and doesn't need admin rights. To remove it, run `ImgConvert.exe --uninstall-context-menu`.

## Windows SmartScreen / "Unknown publisher"

The exe is signed with a self-signed certificate — not one issued by a public CA, since that costs money and requires business identity verification. Its public half is embedded in the app itself (the private key never leaves the dev machine).

On a **new** PC, Windows will still show the SmartScreen warning once — click "More info" > "Run anyway". Then click **"Trust This App"** in the app's header: it silently imports the embedded public cert into that Windows account's Trusted Root + Trusted Publisher stores (no admin needed). After that, this exe — and any future release signed with the same key — won't be flagged on that account again.

## Contributing

Issues and pull requests are welcome. The codebase is a single file (`imgconvert.py`) by design — it's meant to stay small and easy to read end to end.

### Re-signing after a rebuild

If you're building from source and want a signed exe, it must be re-signed every time it's rebuilt (PyInstaller output isn't signed by default):

```powershell
$pfxPath = "signing\imgconvert_signing.pfx"
$plainPassword = Get-Content "signing\pfx_password.txt" -Raw
$securePassword = ConvertTo-SecureString -String $plainPassword -Force -AsPlainText
$cert = Get-PfxCertificate -FilePath $pfxPath -Password $securePassword
Set-AuthenticodeSignature -FilePath "dist\ImgConvert.exe" -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256
```

## License

Copyright © 2026 Joe Wayne / 248Tech LLC. [MIT](LICENSE) — free to use, modify, and redistribute.
