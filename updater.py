"""
updater.py — GitHub Releases based auto-updater for RDX CSB-V Extractor.

A compiled .exe bundles all its libraries — it CANNOT do a live "pip install
--upgrade" on itself. The correct way to ship library updates is:

    1. You push a change / bump version.py / push a tag like "v1.0.1"
    2. .github/workflows/build-release.yml builds a fresh .exe on GitHub's
       Windows runner (with the latest library versions from requirements.txt)
       and publishes it as a GitHub Release automatically.
    3. This module checks that release feed. If a newer version exists, it
       downloads the new .exe and swaps it in place of the running one,
       then relaunches — all without the user doing anything manually.

IMPORTANT: GITHUB_REPO must be just "username/repo" (NOT the full URL,
NOT ending in .git) — it gets plugged into the GitHub API URL below.
"""
import os
import sys
import json
import subprocess
import tempfile
import urllib.request

GITHUB_REPO = "rjgaju2018-droid/rdx-csb-extractor"   # <-- just username/repo
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _current_version():
    from version import __version__
    return __version__


def _parse_ver(v):
    try:
        return tuple(int(p) for p in v.lstrip("v").split("."))
    except Exception:
        return (0,)


def check_for_update(timeout=4):
    """
    Non-destructive check only — safe to call on every startup.
    Returns (has_update: bool, latest_tag: str|None, asset_url: str|None)
    """
    try:
        req = urllib.request.Request(
            API_URL, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)

        latest_tag = data.get("tag_name", "")
        if not latest_tag:
            return False, None, None
        if _parse_ver(latest_tag) <= _parse_ver(_current_version()):
            return False, None, None

        asset_url = None
        for asset in data.get("assets", []):
            if asset["name"].lower().endswith(".exe"):
                asset_url = asset["browser_download_url"]
                break
        if not asset_url:
            return False, None, None

        return True, latest_tag, asset_url
    except Exception:
        # No internet / rate-limited / repo not public yet — fail silently,
        # app should keep working offline regardless.
        return False, None, None


def download_and_apply_update(asset_url, on_progress=None):
    """
    Downloads the new .exe, then spawns a tiny batch script that:
      - waits for this process to fully exit
      - overwrites the old exe with the new one
      - relaunches the app
      - deletes itself
    Only works in the packaged .exe (sys.frozen), not in `python rdx_csb_app.py`.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Auto-update only applies to the packaged .exe build.")

    current_exe = sys.executable
    tmp_dir = tempfile.gettempdir()
    new_exe = os.path.join(tmp_dir, "RDX_CSBV_update.exe")

    with urllib.request.urlopen(asset_url) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        with open(new_exe, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if on_progress and total:
                    on_progress(done / total)

    exe_name = os.path.basename(current_exe)
    bat_path = os.path.join(tmp_dir, "rdx_update.bat")
    with open(bat_path, "w") as f:
        f.write(f"""@echo off
:wait
tasklist /FI "IMAGENAME eq {exe_name}" 2>NUL | find /I "{exe_name}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto wait
)
copy /Y "{new_exe}" "{current_exe}" >NUL
start "" "{current_exe}"
del "%~f0"
""")
    subprocess.Popen(["cmd", "/c", "start", "", bat_path], shell=True)
    sys.exit(0)
