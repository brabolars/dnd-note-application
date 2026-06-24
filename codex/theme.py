"""
theme.py — Theme system, colour tokens, stylesheet factory, UI helpers.

ThemeManager   — loads/saves settings, applies themes app-wide.
build_ss(C)    — generates the full Qt stylesheet from a token dict.
THEMES         — built-in named theme presets.
C              — the currently active colour dict (mutated on theme change).
"""

from __future__ import annotations
import json
import copy
from pathlib import Path
from PyQt6.QtWidgets import QPushButton, QLabel, QFrame, QApplication
from PyQt6.QtCore import Qt


# ── Token definitions for each preset ────────────────────────────────────────
# Every theme must define ALL keys present in THEMES["Codex"].
# The "Custom" theme starts as a copy of Codex and is user-edited.

THEMES: dict[str, dict[str, str]] = {

    "Codex": {                          # original — toned down from launch version
        "bg_deep":       "#111113",
        "bg_panel":      "#17171b",
        "bg_card":       "#1e1e24",
        "bg_hover":      "#26262e",
        "bg_input":      "#131316",
        "border":        "#2e2e3a",
        "border_accent": "#7a1818",
        "crimson":       "#b91c1c",
        "crimson_dim":   "#6f1a1a",
        "crimson_glow":  "#dc2626",
        "gold":          "#b8832e",
        "gold_dim":      "#7a5620",
        "text_primary":  "#ddd5c8",
        "text_muted":    "#6e6660",
        "text_dim":      "#424040",
        "parchment":     "#cbbfa5",
        "green":         "#4ade80",
        "green_bg":      "#172a17",
        "blue":          "#7c86f0",
        "blue_bg":       "#181828",
        "red_text":      "#e06060",
        "red_bg":        "#301515",
        "sky":           "#38bdf8",
        "sky_bg":        "#152535",
        "yellow":        "#e8b84b",
        "yellow_bg":     "#252015",
    },

    "Obsidian": {                       # near-black + cold white, minimal colour
        "bg_deep":       "#0a0a0a",
        "bg_panel":      "#111111",
        "bg_card":       "#181818",
        "bg_hover":      "#202020",
        "bg_input":      "#0d0d0d",
        "border":        "#282828",
        "border_accent": "#444444",
        "crimson":       "#555555",
        "crimson_dim":   "#333333",
        "crimson_glow":  "#cccccc",
        "gold":          "#aaaaaa",
        "gold_dim":      "#555555",
        "text_primary":  "#e8e8e8",
        "text_muted":    "#666666",
        "text_dim":      "#3a3a3a",
        "parchment":     "#d0d0d0",
        "green":         "#88cc88",
        "green_bg":      "#141a14",
        "blue":          "#8899cc",
        "blue_bg":       "#141420",
        "red_text":      "#cc7777",
        "red_bg":        "#1e1212",
        "sky":           "#77aacc",
        "sky_bg":        "#121820",
        "yellow":        "#ccaa66",
        "yellow_bg":     "#1e1a10",
    },

    "Ember": {                          # warm dark browns + burnt orange accent
        "bg_deep":       "#100d0a",
        "bg_panel":      "#17120e",
        "bg_card":       "#1e1812",
        "bg_hover":      "#27201a",
        "bg_input":      "#130f0b",
        "border":        "#352a20",
        "border_accent": "#8b4a1a",
        "crimson":       "#c0622b",
        "crimson_dim":   "#7a3d1a",
        "crimson_glow":  "#e07840",
        "gold":          "#c49a3a",
        "gold_dim":      "#7a6020",
        "text_primary":  "#e0d0bc",
        "text_muted":    "#7a6858",
        "text_dim":      "#4a3e32",
        "parchment":     "#d4be98",
        "green":         "#7abc6a",
        "green_bg":      "#1a2414",
        "blue":          "#8aabcc",
        "blue_bg":       "#141e28",
        "red_text":      "#d08060",
        "red_bg":        "#2a1812",
        "sky":           "#80b8cc",
        "sky_bg":        "#122028",
        "yellow":        "#e0b050",
        "yellow_bg":     "#251e0e",
    },

    "Slate": {                          # cool blue-grays + steel blue accent
        "bg_deep":       "#0c0f12",
        "bg_panel":      "#131820",
        "bg_card":       "#1a2030",
        "bg_hover":      "#222a3a",
        "bg_input":      "#0f1318",
        "border":        "#252e3e",
        "border_accent": "#2a4a6a",
        "crimson":       "#4a7fa5",
        "crimson_dim":   "#2a4f6f",
        "crimson_glow":  "#6aa0c8",
        "gold":          "#7aaa88",
        "gold_dim":      "#3a6a4a",
        "text_primary":  "#c8d8e8",
        "text_muted":    "#5a7080",
        "text_dim":      "#324050",
        "parchment":     "#a8c0d0",
        "green":         "#5abf88",
        "green_bg":      "#102818",
        "blue":          "#7a9cd8",
        "blue_bg":       "#101828",
        "red_text":      "#c07070",
        "red_bg":        "#201418",
        "sky":           "#60b8e0",
        "sky_bg":        "#0e2030",
        "yellow":        "#d4b060",
        "yellow_bg":     "#201c10",
    },

    "Manuscript": {                     # warm parchment light theme
        "bg_deep":       "#f0e8d8",
        "bg_panel":      "#e8dcc8",
        "bg_card":       "#ddd0b8",
        "bg_hover":      "#d0c4a8",
        "bg_input":      "#ede4d2",
        "border":        "#c4b498",
        "border_accent": "#8b4513",
        "crimson":       "#8b4513",
        "crimson_dim":   "#c47a40",
        "crimson_glow":  "#6b2e0a",
        "gold":          "#8b6914",
        "gold_dim":      "#c4a84a",
        "text_primary":  "#2a1e10",
        "text_muted":    "#6a5840",
        "text_dim":      "#9a8870",
        "parchment":     "#1e1408",
        "green":         "#2a5a20",
        "green_bg":      "#d0e0c8",
        "blue":          "#1a3a6a",
        "blue_bg":       "#c8d0e0",
        "red_text":      "#8b2a0a",
        "red_bg":        "#e8d0c8",
        "sky":           "#1a5a8b",
        "sky_bg":        "#c8dce8",
        "yellow":        "#8b6a00",
        "yellow_bg":     "#e8e0c0",
    },
}

# Human-readable labels for the custom colour editor
TOKEN_LABELS: dict[str, str] = {
    "bg_deep":       "Background (deep)",
    "bg_panel":      "Background (panel/sidebar)",
    "bg_card":       "Background (cards)",
    "bg_hover":      "Background (hover state)",
    "bg_input":      "Background (inputs)",
    "border":        "Border",
    "border_accent": "Border (accent/hover)",
    "crimson":       "Accent colour",
    "crimson_dim":   "Accent colour (dim)",
    "crimson_glow":  "Accent colour (bright)",
    "gold":          "Secondary accent",
    "gold_dim":      "Secondary accent (dim)",
    "text_primary":  "Text (primary)",
    "text_muted":    "Text (muted)",
    "text_dim":      "Text (dim)",
    "parchment":     "Text (headings/names)",
    "green":         "Status: alive / safe",
    "green_bg":      "Status: alive / safe (bg)",
    "blue":          "Type: character",
    "blue_bg":       "Type: character (bg)",
    "red_text":      "Status: hostile / dead",
    "red_bg":        "Status: hostile / dead (bg)",
    "sky":           "Type: location",
    "sky_bg":        "Type: location (bg)",
    "yellow":        "Type: lore / neutral",
    "yellow_bg":     "Type: lore / neutral (bg)",
}

# Grouped for the settings UI
TOKEN_GROUPS: list[tuple[str, list[str]]] = [
    ("Backgrounds", ["bg_deep","bg_panel","bg_card","bg_hover","bg_input"]),
    ("Borders",     ["border","border_accent"]),
    ("Accent",      ["crimson","crimson_dim","crimson_glow","gold","gold_dim"]),
    ("Text",        ["text_primary","text_muted","text_dim","parchment"]),
    ("Status / Type colours", [
        "green","green_bg","blue","blue_bg",
        "red_text","red_bg","sky","sky_bg","yellow","yellow_bg"]),
]


# ── Active colour dict (module-level, mutated by ThemeManager) ────────────────
C: dict[str, str] = copy.deepcopy(THEMES["Codex"])


# ── Stylesheet factory ────────────────────────────────────────────────────────

def build_ss(c: dict[str, str]) -> str:
    return f"""
QMainWindow, QWidget {{
    background-color: {c['bg_deep']};
    color: {c['text_primary']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
#sidebar {{
    background-color: {c['bg_panel']};
    border-right: 1px solid {c['border']};
    min-width: 210px; max-width: 210px;
}}
#app_title {{
    font-size: 18px; font-weight: 700;
    color: {c['crimson_glow']}; letter-spacing: 2px;
    padding: 20px 16px 4px 16px;
}}
#app_subtitle {{
    font-size: 10px; color: {c['text_muted']};
    letter-spacing: 3px; padding: 0 16px 16px 16px;
}}
#campaign_label {{ font-size: 10px; color: {c['text_dim']};
    letter-spacing: 2px; padding: 0 16px 2px 16px; }}
#campaign_name {{
    font-size: 12px; font-weight: 600; color: {c['gold']};
    padding: 0 16px 16px 16px;
    border-bottom: 1px solid {c['border']};
}}
QLineEdit, QTextEdit, QComboBox {{
    background-color: {c['bg_input']}; border: 1px solid {c['border']};
    border-radius: 4px; color: {c['text_primary']}; padding: 6px 10px;
    selection-background-color: {c['crimson_dim']};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border-color: {c['crimson']};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {c['bg_card']}; border: 1px solid {c['border']};
    color: {c['text_primary']};
    selection-background-color: {c['crimson_dim']};
}}
QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {c['border']}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['text_dim']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 6px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {c['border']}; border-radius: 3px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c['text_dim']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QTabWidget::pane {{
    border: 1px solid {c['border']}; background: {c['bg_card']};
    border-radius: 0 4px 4px 4px;
}}
QTabBar::tab {{
    background: {c['bg_panel']}; color: {c['text_muted']};
    padding: 7px 20px; border: 1px solid {c['border']};
    border-bottom: none; margin-right: 2px; font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {c['bg_card']}; color: {c['crimson_glow']};
    border-top-color: {c['crimson']};
}}
QTabBar::tab:hover:!selected {{ background: {c['bg_hover']}; color: {c['text_primary']}; }}
QTreeWidget {{ background: transparent; border: none; outline: none;
    alternate-background-color: transparent; }}
QTreeWidget::item {{ padding: 4px 2px; border-radius: 3px; }}
QTreeWidget::item:selected {{ background: {c['bg_hover']}; color: {c['text_primary']}; }}
QTreeWidget::item:hover {{ background: {c['bg_hover']}; }}
QDialog {{ background-color: {c['bg_panel']}; }}
QToolTip {{
    background-color: {c['bg_card']}; color: {c['text_primary']};
    border: 1px solid {c['border']}; padding: 4px 8px; border-radius: 3px;
}}
QCheckBox {{ spacing: 6px; color: {c['text_muted']}; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    background: {c['bg_input']}; border: 1px solid {c['border']}; border-radius: 3px;
}}
QCheckBox::indicator:checked {{ background: {c['crimson']}; border-color: {c['crimson']}; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 4px 2px; border-radius: 3px; }}
QListWidget::item:selected {{ background: {c['bg_hover']}; }}
QStatusBar {{ color: {c['text_muted']}; font-size: 11px; }}
QSlider::groove:horizontal {{
    height: 4px; background: {c['border']}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; height: 14px; margin: -5px 0;
    background: {c['gold']}; border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {c['gold_dim']}; border-radius: 2px;
}}
"""

# Active stylesheet — updated by ThemeManager.apply()
SS: str = build_ss(C)


# ── Settings path ─────────────────────────────────────────────────────────────

def _settings_path() -> Path:
    p = Path.home() / ".codex"
    p.mkdir(exist_ok=True)
    return p / "settings.json"


# ── ThemeManager ──────────────────────────────────────────────────────────────

class ThemeManager:
    """
    Singleton-style manager. Call ThemeManager.instance() to get it.
    Handles load/save of settings and applies themes to the QApplication.
    """
    _instance: "ThemeManager | None" = None

    def __init__(self):
        self._active_name: str = "Codex"
        self._custom: dict[str, str] = copy.deepcopy(THEMES["Codex"])
        self._load()

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self):
        try:
            raw = json.loads(_settings_path().read_text(encoding="utf-8"))
            self._active_name = raw.get("theme", "Codex")
            if "custom_theme" in raw:
                # Only take keys we know about; fill missing ones from Codex
                base = copy.deepcopy(THEMES["Codex"])
                base.update({k: v for k, v in raw["custom_theme"].items() if k in base})
                self._custom = base
        except Exception:
            pass   # first run or corrupt file — use defaults

    def save(self):
        data = {
            "theme": self._active_name,
            "custom_theme": self._custom,
        }
        _settings_path().write_text(
            json.dumps(data, indent=2), encoding="utf-8")

    # ── apply ─────────────────────────────────────────────────────────────────

    def apply(self, name: str | None = None):
        """Apply a named theme (or re-apply current if name is None)."""
        global C, SS
        if name is not None:
            self._active_name = name
        colours = (self._custom if self._active_name == "Custom"
                   else THEMES.get(self._active_name, THEMES["Codex"]))
        C.update(colours)
        SS = build_ss(C)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(SS)
        self.save()

    # ── custom theme editing ──────────────────────────────────────────────────

    @property
    def active_name(self) -> str:
        return self._active_name

    @property
    def custom_colours(self) -> dict[str, str]:
        return self._custom

    def set_custom_colour(self, token: str, hex_value: str):
        self._custom[token] = hex_value
        if self._active_name == "Custom":
            self.apply()   # live preview

    def reset_custom_to(self, preset_name: str):
        self._custom = copy.deepcopy(THEMES.get(preset_name, THEMES["Codex"]))
        if self._active_name == "Custom":
            self.apply()


# ── Widget factories ───────────────────────────────────────────────────────────

def btn(text: str, style: str = "primary") -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    _s = {
        "primary":   f"background:{C['crimson']};border:none;border-radius:4px;color:white;padding:7px 18px;font-weight:600;font-size:12px;",
        "secondary": f"background:transparent;border:1px solid {C['border']};border-radius:4px;color:{C['text_muted']};padding:7px 18px;font-size:12px;",
        "danger":    f"background:transparent;border:1px solid {C['crimson_dim']};border-radius:4px;color:{C['crimson_glow']};padding:5px 14px;font-size:12px;",
        "gold":      f"background:transparent;border:1px solid {C['gold_dim']};border-radius:4px;color:{C['gold']};padding:7px 18px;font-size:12px;font-weight:600;",
        "icon":      f"background:transparent;border:1px solid {C['border']};border-radius:4px;color:{C['text_muted']};padding:4px 8px;font-size:11px;",
    }
    _h = {
        "primary":   f"background:{C['crimson_glow']};",
        "secondary": f"border-color:{C['border_accent']};color:{C['text_primary']};",
        "danger":    f"background:{C['crimson_dim']};",
        "gold":      f"background:{C['gold_dim']};color:{C['parchment']};",
        "icon":      f"border-color:{C['border_accent']};color:{C['text_primary']};",
    }
    b.setStyleSheet(
        f"QPushButton{{{_s.get(style,_s['secondary'])}}}"
        f"QPushButton:hover{{{_h.get(style,'')}}}"
    )
    return b


def lbl(text: str, color: str | None = None, size: int | None = None,
        bold: bool = False, spacing: int = 0) -> QLabel:
    l = QLabel(text)
    css = f"color:{color or C['text_muted']};"
    if size:    css += f"font-size:{size}px;"
    if bold:    css += "font-weight:700;"
    if spacing: css += f"letter-spacing:{spacing}px;"
    l.setStyleSheet(css)
    return l


def field_lbl(text: str) -> QLabel:
    return lbl(text, C['text_muted'], 11)


def sep_h() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{C['border']};margin:6px 0;")
    return f


def sep_v() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet(f"color:{C['border']};margin:0 2px;")
    return f