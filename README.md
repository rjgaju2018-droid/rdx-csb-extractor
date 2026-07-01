# RDX Solution — CSB-V Shipping Bill Extractor

Desktop app (login + dashboard + processing window) that extracts shipping-bill
data from CSB-V PDFs into a formatted Excel file. Ships as a Windows `.exe`
that auto-updates itself via GitHub Releases.

## Project structure

```
rdx-csb-extractor/
├── rdx_csb_app.py              # main app (UI + extraction engine)
├── updater.py                  # GitHub-Releases based auto-updater
├── version.py                  # single source of truth for the app version
├── requirements.txt            # runtime dependencies
├── requirements-build.txt      # build-only dependency (PyInstaller)
├── build.spec                  # PyInstaller spec (onefile, windowed)
├── .github/workflows/
│   └── build-release.yml       # auto-builds the .exe on every version tag
├── .gitignore
└── README.md
```

## 1. Push this to GitHub

```bash
cd rdx-csb-extractor
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/rdx-csb-extractor.git
git push -u origin main
```

## 2. Point the updater at your repo

Open `updater.py` and change:

```python
GITHUB_REPO = "YOUR_GITHUB_USERNAME/rdx-csb-extractor"
```

to your actual `username/repo`. Commit and push that change before your
first release.

## 3. Run locally (no exe needed, for development)

```bash
pip install -r requirements.txt
python rdx_csb_app.py
```

You also need **Tesseract OCR** installed on your system (only used as a
fallback for scanned/image-only PDFs):
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt install tesseract-ocr`
- Mac: `brew install tesseract`

## 4. Cutting a release (this is what makes the auto-update work)

Whenever you want to ship an update — e.g. because a library version bumped,
or you fixed extraction logic:

1. Bump the version in `version.py`, e.g. `__version__ = "1.0.1"`
2. Commit it
3. Tag and push:
   ```bash
   git add version.py
   git commit -m "Bump version to 1.0.1"
   git tag v1.0.1
   git push origin main --tags
   ```
4. GitHub Actions (`.github/workflows/build-release.yml`) automatically:
   - spins up a Windows runner
   - installs everything fresh from `requirements.txt` (so library updates
     are picked up automatically)
   - builds `RDX_CSBV_Extractor.exe` with PyInstaller
   - publishes it as a GitHub Release

No manual exe building required after the first setup — just tag and push.

## 5. How the auto-update actually works on a user's machine

- Every time the Dashboard opens, the app quietly checks
  `github.com/<repo>/releases/latest` in a background thread (never blocks
  the UI).
- If a newer version is published, a small gold banner appears on the
  Dashboard: **"New version vX.X.X available"** with an **Update Now** button.
- Clicking it downloads the new `.exe`, then hands off to a tiny batch
  script that waits for the app to close, swaps the old exe for the new
  one, and relaunches automatically.
- If there's no internet or GitHub is unreachable, the check fails silently
  and the app just keeps working normally — it never blocks startup.

**Note:** this only works in the packaged `.exe` build (`sys.frozen`), not
when running `python rdx_csb_app.py` directly.

## 6. Building the EXE manually (optional — CI does this for you)

```bash
pip install -r requirements.txt -r requirements-build.txt
pyinstaller build.spec
```

Output: `dist/RDX_CSBV_Extractor.exe`

### Why onefile, and the speed trade-off

`build.spec` builds a **single-file** exe on purpose — that's what lets
`updater.py` cleanly swap the old exe for the new one on update. The
trade-off is a slightly slower first launch (a few hundred ms) because
onefile exes unpack themselves into a temp folder on each run. If you'd
rather prioritize raw startup speed over easy self-updating, switch
`build.spec` to a `COLLECT()`-based onedir build and distribute the whole
folder — but then updates have to replace multiple files, so you'd need to
extend `updater.py` accordingly.

### Avoiding "hangs" on the target machine

- All PDF parsing/OCR happens on a background `threading.Thread`
  (`ProcessingWindow._proc_thread`) — the UI thread is never blocked, so the
  window stays responsive even on large batches.
- UPX compression is turned **off** in `build.spec` — UPX-compressed exes
  are a common false-positive trigger for antivirus/SmartScreen, which can
  cause multi-second startup delays or outright blocking on locked-down
  corporate machines.
- OCR fallback only kicks in for PDFs with no text layer, so normal
  digitally-generated CSB-V bills stay on the fast `pdfplumber` path.
