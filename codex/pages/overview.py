"""
overview.py — OverviewPage panel.
"""

from __future__ import annotations
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QComboBox, QDialog,
    QScrollArea, QMessageBox, QFileDialog, QGridLayout,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QCheckBox,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsLineItem, QGraphicsItem,
    QColorDialog,
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPen, QPainter, QFont, QKeySequence, QPixmap, QShortcut

from codex.theme import C, SS, btn, lbl, field_lbl, sep_h, sep_v
from codex.models import new_campaign, new_character, new_session, new_lore, new_location
from codex.widgets.common import EmptyState, TagBadge, _BaseDialog
from codex.widgets.dialogs import CharacterDialog, SessionDialog, LoreDialog, LocationDialog


class OverviewPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent); self.app = app; self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(28,24,28,24); vl.setSpacing(18)
        vl.addWidget(lbl("CAMPAIGN OVERVIEW", C['text_dim'], 11, True, 2))

        meta = QFrame()
        meta.setStyleSheet(f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};border-radius:6px;}}")
        ml = QGridLayout(meta); ml.setContentsMargins(16,14,16,14); ml.setSpacing(10)
        ml.setColumnStretch(1,1); ml.setColumnStretch(3,1)

        ml.addWidget(field_lbl("CAMPAIGN NAME"), 0, 0)
        self.name_e = QLineEdit(); self.name_e.setPlaceholderText("Name…"); ml.addWidget(self.name_e, 1, 0)
        ml.addWidget(field_lbl("DUNGEON MASTER"), 0, 2)
        self.dm_e = QLineEdit(); self.dm_e.setPlaceholderText("DM…"); ml.addWidget(self.dm_e, 1, 2)
        ml.addWidget(field_lbl("SETTING / WORLD"), 2, 0)
        self.setting_e = QLineEdit(); self.setting_e.setPlaceholderText("Forgotten Realms, homebrew…")
        ml.addWidget(self.setting_e, 3, 0, 1, 3)
        ml.addWidget(field_lbl("CAMPAIGN NOTES"), 4, 0, 1, 4)
        self.notes_e = QTextEdit(); self.notes_e.setPlaceholderText("Overall arc, party details…")
        self.notes_e.setMinimumHeight(90); ml.addWidget(self.notes_e, 5, 0, 1, 4)
        sv = btn("Save Overview", "primary"); sv.clicked.connect(self._save)
        ml.addWidget(sv, 6, 3)
        vl.addWidget(meta)

        self._stats_row = QHBoxLayout(); self._stats_row.setSpacing(10)
        vl.addLayout(self._stats_row)
        vl.addStretch()
        self.refresh()

    def _stat(self, label, value, color):
        w = QFrame()
        w.setStyleSheet(f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
                        f"border-top:2px solid {color};border-radius:6px;}}")
        vl = QVBoxLayout(w); vl.setContentsMargins(14,10,14,10)
        vl.addWidget(lbl(str(value), color, 28, True))
        vl.addWidget(lbl(label, C['text_muted'], 10, spacing=1))
        return w

    def refresh(self):
        d = self.app.campaign
        self.name_e.setText(d["meta"].get("name",""))
        self.dm_e.setText(d["meta"].get("dm",""))
        self.setting_e.setText(d["meta"].get("setting",""))
        self.notes_e.setPlainText(d["meta"].get("notes",""))
        while self._stats_row.count():
            it = self._stats_row.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        chars = d.get("characters",[])
        locs  = d.get("locations",[])
        for label, val, col in [
            ("SESSIONS",   len(d.get("sessions",[])),                       C['crimson_glow']),
            ("CHARACTERS", len(chars),                                        C['gold']),
            ("ALLIES",     sum(1 for c in chars if c.get("role")=="Ally"),   C['sky']),
            ("ENEMIES",    sum(1 for c in chars if c.get("role")=="Enemy"),  C['red_text']),
            ("LOCATIONS",  len(locs),                                         C['green']),
            ("LORE",       len(d.get("lore",[])),                             C['blue']),
        ]:
            self._stats_row.addWidget(self._stat(label, val, col))

    def _save(self):
        m = self.app.campaign["meta"]
        m["name"] = self.name_e.text().strip()
        m["dm"]   = self.dm_e.text().strip()
        m["setting"] = self.setting_e.text().strip()
        m["notes"]   = self.notes_e.toPlainText().strip()
        m["modified"] = datetime.now().isoformat()
        self.app.update_campaign_label(); self.app.set_dirty(True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: CHARACTERS
# ══════════════════════════════════════════════════════════════════════════════
