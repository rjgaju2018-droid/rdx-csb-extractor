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
alt_logo_path = os.path.join(ROOT, "rdx_solution_logo.png")
icon_path = os.path.join(ROOT, "icon.ico")
env_path = os.path.join(ROOT, ".env")
courier_tracker_dir = os.path.join(ROOT, "carriers", "courier_tracker")
courier_config_path = os.path.join(courier_tracker_dir, "config.json")

if os.path.exists(logo_path):
    datas.append((logo_path, "."))
if os.path.exists(alt_logo_path):
    datas.append((alt_logo_path, "."))
if os.path.exists(icon_path):
    datas.append((icon_path, "."))   # bundled so the running window can set its own titlebar/taskbar icon
if os.path.exists(env_path):
    # Supabase (and other) credentials. auth/supabase_client.py and
    # carriers/gateways.py both resolve this relative to sys._MEIPASS at
    # runtime, so it MUST be bundled here or login/karrio will raise
    # "Missing Supabase credentials" even though the .env exists on disk.
    datas.append((env_path, "."))
if os.path.exists(courier_config_path):
    # Blank/default template only — the app copies real, user-entered keys to
    # a persistent courier_config.json next to the .exe (see
    # CourierTrackerPage._persistent_config_path in rdx_csb_app.py), because
    # anything under sys._MEIPASS is wiped after the app closes.
    datas.append((courier_config_path, "carriers/courier_tracker"))

a = Analysis(
    [os.path.join(ROOT, "rdx_csb_app.py")],
    # Include the courier_tracker folder in pathex so PyInstaller's static
    # analysis can actually find "tracker_engine" — it's imported as a bare
    # module name (via a runtime sys.path.insert) rather than as
    # carriers.courier_tracker.tracker_engine, so without this pathex entry
    # PyInstaller silently leaves it out and the Multi-Courier Tracker page
    # shows "engine not found" in the packaged .exe even though it works
    # fine when running from source.
    pathex=[ROOT, courier_tracker_dir],
    binaries=[],
    datas=datas,
    hiddenimports=["pytesseract", "fitz", "PIL._tkinter_finder", "tracker_engine", "requests"],
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
