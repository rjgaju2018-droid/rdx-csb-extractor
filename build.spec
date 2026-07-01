# Build locally with:  pyinstaller build.spec
# (GitHub Actions runs this exact same command automatically on every release tag)

import os
block_cipher = None

# Use the spec file's own folder (SPECPATH) instead of the current working
# directory. If `pyinstaller build.spec` is ever run from a different
# folder, relative "logo.png" checks would silently fail and the exe would
# ship WITHOUT the logo/icon baked in (this is what caused the login page
# to show fallback text instead of the big RDX logo image).
ROOT = SPECPATH

datas = []
logo_path = os.path.join(ROOT, "logo.png")
alt_logo_path = os.path.join(ROOT, "rdx_soloution_logo.png")
icon_path = os.path.join(ROOT, "icon.ico")

if os.path.exists(logo_path):
    datas.append((logo_path, "."))
if os.path.exists(alt_logo_path):
    datas.append((alt_logo_path, "."))
if os.path.exists(icon_path):
    datas.append((icon_path, "."))   # bundled so the running window can set its own titlebar/taskbar icon

a = Analysis(
    [os.path.join(ROOT, "rdx_csb_app.py")],
    pathex=[ROOT],
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
    icon=icon_path if os.path.exists(icon_path) else None,
)
# NOTE: passing a.binaries / a.zipfiles / a.datas directly into EXE() (instead
# of a separate COLLECT() step) is what makes this a single-file "onefile"
# build — a single .exe that the updater.py module can cleanly replace.
