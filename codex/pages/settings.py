"""
settings.py — SettingsPage: theme picker + custom colour editor.
7th sidebar item. Changes apply live; saved to ~/.codex/settings.json.
"""

from __future__ import annotations
import copy

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QColorDialog, QMessageBox,
    QComboBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from codex.theme import (
    C, THEMES, TOKEN_LABELS, TOKEN_GROUPS,
    ThemeManager, btn, lbl, sep_h, build_ss,
)


class ThemeCard(QWidget):
    """Clickable preview card for a preset theme."""

    def __init__(self, name: str, colours: dict, is_active: bool,
                 on_select, parent=None):
        super().__init__(parent)
        self._name = name
        self._on_select = on_select
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_active = is_active
        self._colours = colours
        self._build(colours, is_active)

    def _build(self, c: dict, active: bool):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(12, 10, 12, 10)
        vl.setSpacing(6)

        border = c['crimson'] if active else c['border']
        self.setStyleSheet(f"""
            ThemeCard {{
                background: {c['bg_panel']};
                border: 2px solid {border};
                border-radius: 8px;
            }}
            ThemeCard:hover {{
                border-color: {c['crimson_glow']};
            }}
        """)

        # Mini colour strip
        strip = QHBoxLayout(); strip.setSpacing(3); strip.setContentsMargins(0,0,0,0)
        for col in [c['bg_deep'], c['bg_panel'], c['crimson_glow'],
                    c['gold'], c['text_primary']]:
            dot = QLabel()
            dot.setFixedSize(16, 16)
            dot.setStyleSheet(f"background:{col};border-radius:8px;")
            strip.addWidget(dot)
        strip.addStretch()
        if active:
            badge = QLabel("ACTIVE")
            badge.setStyleSheet(
                f"background:{c['crimson']};color:white;"
                f"border-radius:3px;padding:1px 6px;font-size:9px;font-weight:700;")
            strip.addWidget(badge)
        vl.addLayout(strip)

        # Name
        name_lbl = QLabel(self._name)
        name_lbl.setStyleSheet(
            f"color:{c['text_primary']};font-size:13px;font-weight:600;")
        vl.addWidget(name_lbl)

        # Mini preview bar
        preview = QFrame()
        preview.setFixedHeight(6)
        preview.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {c['crimson']}, stop:0.5 {c['gold']}, stop:1 {c['sky']});"
            f"border-radius:3px;")
        vl.addWidget(preview)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_select(self._name)
        super().mousePressEvent(event)


class ColourRow(QWidget):
    """One row in the custom editor: label + swatch button."""

    def __init__(self, token: str, hex_value: str, on_change, parent=None):
        super().__init__(parent)
        self.token = token
        self._on_change = on_change
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 2, 0, 2)
        hl.setSpacing(10)

        self._label = QLabel(TOKEN_LABELS.get(token, token))
        self._label.setStyleSheet(f"color:{C['text_muted']};font-size:11px;")
        self._label.setMinimumWidth(220)
        hl.addWidget(self._label)

        self._hex_lbl = QLabel(hex_value.upper())
        self._hex_lbl.setStyleSheet(
            f"color:{C['text_dim']};font-size:10px;font-family:monospace;")
        self._hex_lbl.setMinimumWidth(70)
        hl.addWidget(self._hex_lbl)

        self._swatch = QPushButton()
        self._swatch.setFixedSize(32, 20)
        self._swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_swatch(hex_value)
        self._swatch.clicked.connect(self._pick)
        hl.addWidget(self._swatch)
        hl.addStretch()

        self._current = hex_value

    def _update_swatch(self, hex_value: str):
        self._swatch.setStyleSheet(
            f"background:{hex_value};border:1px solid {C['border']};"
            f"border-radius:3px;")

    def _pick(self):
        col = QColorDialog.getColor(QColor(self._current), self, "Pick colour")
        if col.isValid():
            self._current = col.name()
            self._update_swatch(self._current)
            self._hex_lbl.setText(self._current.upper())
            self._on_change(self.token, self._current)

    def set_value(self, hex_value: str):
        self._current = hex_value
        self._update_swatch(hex_value)
        self._hex_lbl.setText(hex_value.upper())


class SettingsPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._tm = ThemeManager.instance()
        self._colour_rows: dict[str, ColourRow] = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        root.addWidget(lbl("APPEARANCE", C['text_dim'], 11, True, 2))

        # ── Theme cards ───────────────────────────────────────────────────
        root.addWidget(lbl("Theme", C['parchment'], 13, True))

        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(12)
        self._build_cards()
        root.addLayout(self._cards_row)

        root.addWidget(sep_h())

        # ── Custom editor ─────────────────────────────────────────────────
        custom_hdr = QHBoxLayout()
        custom_hdr.addWidget(lbl("Custom Theme", C['parchment'], 13, True))
        custom_hdr.addStretch()

        # Reset custom to a preset
        self._reset_combo = QComboBox()
        self._reset_combo.addItems(list(THEMES.keys()))
        self._reset_combo.setMaximumWidth(130)
        self._reset_combo.setStyleSheet(
            f"background:{C['bg_input']};border:1px solid {C['border']};"
            f"border-radius:4px;color:{C['text_primary']};padding:3px 6px;font-size:11px;")
        custom_hdr.addWidget(lbl("Reset from:", C['text_muted'], 11))
        custom_hdr.addWidget(self._reset_combo)

        reset_btn = btn("Reset", "secondary")
        reset_btn.clicked.connect(self._reset_custom)
        custom_hdr.addWidget(reset_btn)

        use_btn = btn("Use Custom", "primary")
        use_btn.clicked.connect(lambda: self._select_theme("Custom"))
        custom_hdr.addWidget(use_btn)
        root.addLayout(custom_hdr)

        root.addWidget(lbl(
            "Click any swatch to change that colour. Changes preview live when Custom is active.",
            C['text_dim'], 10))

        # Scrollable colour editor
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0); il.setSpacing(4)

        for group_name, tokens in TOKEN_GROUPS:
            grp_lbl = QLabel(group_name.upper())
            grp_lbl.setStyleSheet(
                f"color:{C['text_dim']};font-size:9px;letter-spacing:2px;"
                f"font-weight:600;padding-top:10px;")
            il.addWidget(grp_lbl)
            il.addWidget(sep_h())
            for token in tokens:
                val = self._tm.custom_colours.get(token, "#000000")
                row = ColourRow(token, val, self._on_colour_changed)
                self._colour_rows[token] = row
                il.addWidget(row)

        il.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

    def _build_cards(self):
        while self._cards_row.count():
            it = self._cards_row.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        active = self._tm.active_name
        all_themes = list(THEMES.keys()) + ["Custom"]
        for name in all_themes:
            colours = (self._tm.custom_colours if name == "Custom"
                       else THEMES[name])
            card = ThemeCard(name, colours, name == active,
                             on_select=self._select_theme)
            card.setMinimumWidth(140)
            card.setMaximumWidth(200)
            self._cards_row.addWidget(card)
        self._cards_row.addStretch()

    def _select_theme(self, name: str):
        self._tm.apply(name)
        # Rebuild cards to update ACTIVE badge
        self._build_cards()
        # Notify app to re-apply stylesheet to main window
        if hasattr(self.app, '_apply_theme'):
            self.app._apply_theme()

    def _on_colour_changed(self, token: str, hex_value: str):
        self._tm.set_custom_colour(token, hex_value)
        if hasattr(self.app, '_apply_theme'):
            self.app._apply_theme()

    def _reset_custom(self):
        preset = self._reset_combo.currentText()
        if QMessageBox.question(
            self, "Reset Custom Theme",
            f"Reset your custom theme to '{preset}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self._tm.reset_custom_to(preset)
        # Update all swatch rows
        for token, row in self._colour_rows.items():
            row.set_value(self._tm.custom_colours.get(token, "#000000"))
        if hasattr(self.app, '_apply_theme'):
            self.app._apply_theme()

    def refresh(self):
        pass   # nothing campaign-specific to reload