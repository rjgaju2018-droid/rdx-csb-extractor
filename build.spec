# Build locally with:  pyinstaller build.spec
# (GitHub Actions runs this exact same command automatically on every release tag)

block_cipher = None

# Optional assets — remove these lines from `datas` / `icon` if you don't have
# a logo.png / icon.ico in the repo root.
datas = []
import os
if os.path.exists("logo.png"):
    datas.append(("logo.png", "."))
if os.path.exists("rdx_soloution_logo.png"):
    datas.append(("rdx_soloution_logo.png", "."))
if os.path.exists("icon.ico"):
    datas.append(("icon.ico", "."))   # bundled so the running window can set its own titlebar/taskbar icon

a = Analysis(
    ["rdx_csb_app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["pytesseract", "fitz", "PIL._tkinter_finder"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="RDX_CSBV_Extractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can trigger antivirus false-positives & slows first run
    console=False,       # windowed app, no terminal popup
    icon="icon.ico" if os.path.exists("icon.ico") else None,
)
# NOTE: passing a.binaries / a.zipfiles / a.datas directly into EXE() (instead
# of a separate COLLECT() step) is what makes this a single-file "onefile"
# build — a single .exe that the updater.py module can cleanly replace.
