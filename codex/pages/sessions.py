"""
sessions.py — SessionsPage panel.
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


class SessionsPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent); self.app = app; self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(28,24,28,24); vl.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(lbl("SESSIONS", C['text_dim'], 11, True, 2)); top.addStretch()
        add = btn("+ Log Session","primary"); add.clicked.connect(self._add)
        top.addWidget(add); vl.addLayout(top)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cont = QWidget(); self._cl = QVBoxLayout(self._cont)
        self._cl.setSpacing(8); self._cl.setContentsMargins(0,0,0,0)
        self._cl.addStretch(); scroll.setWidget(self._cont); vl.addWidget(scroll)
        self.refresh()

    def refresh(self):
        while self._cl.count() > 1:
            it = self._cl.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        sessions = self.app.campaign.get("sessions",[])
        if not sessions:
            self._cl.insertWidget(0, EmptyState("📜","No sessions logged",
                "Record your first session.")); return
        for i, s in enumerate(sessions):
            card = self._make_card(s, i, len(sessions))
            self._cl.insertWidget(self._cl.count()-1, card)

    def _make_card(self, s, idx, total):
        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
                           f"border-radius:6px;}}QFrame:hover{{border-color:{C['border_accent']};"
                           f"background:{C['bg_hover']};}}")
        hl = QHBoxLayout(card); hl.setContentsMargins(14,11,14,11)

        # Reorder arrows
        arr = QVBoxLayout(); arr.setSpacing(2)
        up = btn("▲","icon"); up.setFixedSize(26,22)
        up.setEnabled(idx > 0)
        up.clicked.connect(lambda _, i=idx: self._move(i, -1))
        dn = btn("▼","icon"); dn.setFixedSize(26,22)
        dn.setEnabled(idx < total-1)
        dn.clicked.connect(lambda _, i=idx: self._move(i, 1))
        arr.addWidget(up); arr.addWidget(dn); hl.addLayout(arr)

        num = lbl(f"#{idx+1:02d}", C['crimson_dim'], 22, True)
        num.setMinimumWidth(48); hl.addWidget(num)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{C['border']};"); hl.addWidget(sep)

        content = QVBoxLayout(); content.setSpacing(3); content.setContentsMargins(10,0,0,0)
        content.addWidget(lbl(s.get("name","Unnamed"), C['parchment'], 13, True))
        content.addWidget(lbl(s.get("date",""), C['text_muted'], 11))
        if s.get("summary"):
            p = s["summary"][:100].replace("\n"," ") + ("…" if len(s["summary"])>100 else "")
            content.addWidget(lbl(p, C['text_dim'], 11))
        if s.get("linked"):
            content.addWidget(lbl("🔗 " + "  ·  ".join(l["label"] for l in s["linked"][:4]),
                                   C['blue'], 10))
        hl.addLayout(content); hl.addStretch()

        edit = btn("Edit","icon"); edit.setFixedWidth(50)
        edit.clicked.connect(lambda _, ss=s: self._edit(ss))
        hl.addWidget(edit)
        return card

    def _move(self, idx, direction):
        lst = self.app.campaign["sessions"]
        ni = idx + direction
        if 0 <= ni < len(lst):
            lst[idx], lst[ni] = lst[ni], lst[idx]
            self.app.set_dirty(True); self.refresh()

    def _add(self):
        dlg = SessionDialog(campaign=self.app.campaign, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.app.campaign["sessions"].append(dlg.get_data())
            self.app.set_dirty(True); self.refresh()

    def _edit(self, s):
        dlg = SessionDialog(data=s, campaign=self.app.campaign, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_data()
            lst = self.app.campaign["sessions"]
            for i,ss in enumerate(lst):
                if ss["id"] == updated["id"]: lst[i] = updated; break
            self.app.set_dirty(True); self.refresh()

    def _delete(self, eid):
        self.app.campaign["sessions"] = [
            s for s in self.app.campaign["sessions"] if s["id"] != eid]
        self.app.set_dirty(True); self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: LOCATIONS  (hierarchical tree + detail panel + map tab)
# ══════════════════════════════════════════════════════════════════════════════

LOC_STATUS_COL = {
    "Safe":      C['green'],  "Hostile":   C['red_text'],
    "Contested": C['yellow'], "Unknown":   C['text_muted'],
    "Visited":   C['sky'],    "Destroyed": C['text_dim'],
}
LOC_TYPE_ICON = {
    "City":"🏙","Town":"🏘","Village":"🏡","Dungeon":"⛏","Tavern":"🍺",
    "Temple":"⛪","Wilderness":"🌲","Ruin":"🏚","Region":"🗺","Fortress":"🏰","Other":"📍",
}
