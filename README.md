# ImgConvert

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Small local GUI tool to batch-convert images between JPEG/JPG, PNG, WebP, GIF, TIFF/TIF, and HEIC/HEIF.

## Download

Grab the latest Windows exe from the [Releases](../../releases) page — no Python install needed.

## Setup

```
pip install -r requirements.txt
```

`tkinterdnd2` is optional — if it's missing, the app still works, you just use the "Add Files…" / "Add Folder…" buttons instead of drag-and-drop.

## Run

```
python imgconvert.py
```

## Use

1. Drag files/folders onto the window (or click "Add Files…" / "Add Folder…").
2. Pick the target format from the dropdown.
3. Pick an output folder (defaults to a `converted/` subfolder next to the first file).
4. Click "Convert".

Files that fail to convert (not an image, corrupt, etc.) are skipped and listed in the log — the rest of the batch still runs.

## Windows SmartScreen / "Unknown publisher"

The exe is signed with a self-signed certificate (`signing/imgconvert_signing.pfx`, local to this machine — never share it or `pfx_password.txt`). Its public half is embedded in the app.

On a **new** PC, Windows will still show the SmartScreen warning once — click "More info" > "Run anyway". Then click **"Trust This App"** in the app's header: it silently imports the embedded public cert into that Windows account's Trusted Root + Trusted Publisher stores (no admin needed). After that, this exe — and any future rebuild signed with the same key — won't be flagged on that account again.

### Re-signing after a rebuild

The exe must be re-signed every time it's rebuilt (PyInstaller output isn't signed by default):

```powershell
$pfxPath = "signing\imgconvert_signing.pfx"
$plainPassword = Get-Content "signing\pfx_password.txt" -Raw
$securePassword = ConvertTo-SecureString -String $plainPassword -Force -AsPlainText
$cert = Get-PfxCertificate -FilePath $pfxPath -Password $securePassword
Set-AuthenticodeSignature -FilePath "dist\ImgConvert.exe" -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256
```
