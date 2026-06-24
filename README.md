# ⚔ Codex — D&D Campaign Tracker

Track your campaigns: characters, locations, lore, maps, and the web of connections between them.

## Quick start (developers / nerds)

```bash
git clone https://github.com/<you>/codex
cd codex
pip install -e .
codex
```

Requires Python 3.11+ and PyQt6.

## For everyone else

Download **Codex.exe** from the [latest Release](../../releases/latest).  
Double-click. No Python needed.

## Save files

Campaigns are saved as `.dndbook` files — these are just JSON with a custom extension, so they're human-readable and won't get corrupted. Back them up like any other document.

## Releasing a new version

1. Update `__version__` in `codex/__init__.py`
2. Add an entry to `CHANGELOG.md`
3. `git tag v1.x && git push origin v1.x`

GitHub Actions will build `Codex.exe` and publish it as a Release automatically.

## Building locally

```bash
pip install pyinstaller
python build.py
# → dist/Codex.exe
```
