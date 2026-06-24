"""
build.py — PyInstaller packaging script.
Run from repo root:  python build.py

Produces:  dist/Codex.exe  (Windows, single file, no console window)
"""

import subprocess, sys, shutil, pathlib

ROOT  = pathlib.Path(__file__).parent
DIST  = ROOT / "dist"
BUILD = ROOT / "build"

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "Codex",
    "--clean",
    # Uncomment and point to your icon when you have one:
    # "--icon", "codex/assets/icon.ico",
    "codex/main.py",
]

print("Running PyInstaller…")
result = subprocess.run(cmd, cwd=ROOT)

if result.returncode == 0:
    exe = DIST / "Codex.exe"
    if exe.exists():
        print(f"\n✓ Build successful: {exe}")
    else:
        print(f"\n✓ Build finished — check {DIST}/")
else:
    print("\n✗ Build failed")
    sys.exit(1)
