# Changelog

All notable changes to Codex are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.0.0] — Initial structured release
### Added
- Campaign overview with live stats
- Characters page — cards, role/status badges, search, filter by role
- Sessions page — numbered log with reorder arrows
- Locations page — hierarchical tree (regions → sub-locations), Notes / Secrets & Loot tabs
- Map tab (inside Locations) — pan, zoom, calibrate scale, measure distances, import old JSON
- Lore page — categories, filter pills
- Connections page — multi-ring radial graph, draw mode for visual annotations
- Full linking system across all entry types
- Save format: `.dndbook` (JSON), with save_version field for future migrations
- `codex` command-line entry point via `pip install -e .`
