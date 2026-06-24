"""
characters.py — CharactersPage panel.
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


class CharactersPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent); self.app = app
        self._filter = "All"; self._search = ""; self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(28,24,28,24); vl.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(lbl("CHARACTERS", C['text_dim'], 11, True, 2))
        top.addStretch()
        self.search_e = QLineEdit(); self.search_e.setPlaceholderText("Search…")
        self.search_e.setFixedWidth(200); self.search_e.textChanged.connect(self._on_search)
        top.addWidget(self.search_e)
        add = btn("+ Add Character", "primary"); add.clicked.connect(self._add)
        top.addWidget(add); vl.addLayout(top)

        pill_row = QHBoxLayout(); self._pills = {}
        for role in ["All","Ally","Enemy","NPC","Neutral","Player"]:
            b = QPushButton(role); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, r=role: self._set_filter(r))
            self._pills[role] = b; self._style_pill(b, role=="All")
            pill_row.addWidget(b)
        pill_row.addStretch(); vl.addLayout(pill_row)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cont = QWidget(); self._cl = QVBoxLayout(self._cont)
        self._cl.setSpacing(8); self._cl.setContentsMargins(0,0,0,0)
        self._cl.addStretch(); scroll.setWidget(self._cont); vl.addWidget(scroll)
        self.refresh()

    def _style_pill(self, b, active):
        if active:
            b.setStyleSheet(f"QPushButton{{background:{C['crimson_dim']};border:1px solid {C['crimson']};"
                            f"color:{C['parchment']};border-radius:12px;padding:4px 14px;"
                            f"font-size:11px;font-weight:600;}}")
        else:
            b.setStyleSheet(f"QPushButton{{background:transparent;border:1px solid {C['border']};"
                            f"color:{C['text_muted']};border-radius:12px;padding:4px 14px;font-size:11px;}}"
                            f"QPushButton:hover{{border-color:{C['border_accent']};"
                            f"color:{C['text_primary']};}}")

    def _set_filter(self, role):
        self._filter = role
        for r, b in self._pills.items(): self._style_pill(b, r == role)
        self.refresh()

    def _on_search(self, t): self._search = t.lower(); self.refresh()

    def refresh(self):
        while self._cl.count() > 1:
            it = self._cl.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        chars = self.app.campaign.get("characters", [])
        if self._filter != "All":
            chars = [c for c in chars if c.get("role") == self._filter]
        if self._search:
            chars = [c for c in chars if
                     self._search in c.get("name","").lower() or
                     self._search in c.get("notes","").lower() or
                     self._search in c.get("race","").lower()]
        if not chars:
            self._cl.insertWidget(0, EmptyState("🎭","No characters yet",
                "Add the NPCs, allies, and enemies you encounter.")); return
        for ch in chars:
            card = self._make_card(ch)
            self._cl.insertWidget(self._cl.count()-1, card)

    def _make_card(self, ch):
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
                           f"border-radius:6px;}}QFrame:hover{{border-color:{C['border_accent']};"
                           f"background:{C['bg_hover']};}}")
        vl = QVBoxLayout(card); vl.setContentsMargins(14,11,14,11); vl.setSpacing(5)
        top = QHBoxLayout()
        top.addWidget(lbl(ch.get("name","Unknown"), C['parchment'], 14, True))
        top.addStretch()
        top.addWidget(TagBadge(ch.get("role","NPC"), ch.get("role")))
        vl.addLayout(top)
        details = "  ·  ".join(filter(None,[ch.get("race"),ch.get("class_or_job")]))
        if details: vl.addWidget(lbl(details, C['text_muted'], 11))
        if ch.get("notes"):
            p = ch["notes"][:120].replace("\n"," ") + ("…" if len(ch["notes"])>120 else "")
            vl.addWidget(lbl(p, C['text_dim'], 11))
        status_col = {"Alive":C['green'],"Dead":C['red_text'],"Unknown":C['gold'],"Missing":C['gold']}
        vl.addWidget(lbl(f"● {ch.get('status','Alive')}", status_col.get(ch.get("status","Alive"),C['text_muted']), 10))
        if ch.get("linked"):
            link_txt = "🔗 " + "  ·  ".join(l["label"] for l in ch["linked"][:4])
            vl.addWidget(lbl(link_txt, C['blue'], 10))
        card.mousePressEvent = lambda e, c=ch: self._edit(c)
        return card

    def _add(self):
        dlg = CharacterDialog(campaign=self.app.campaign, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.app.campaign["characters"].append(dlg.get_data())
            self.app.set_dirty(True); self.refresh()

    def _edit(self, ch):
        dlg = CharacterDialog(data=ch, campaign=self.app.campaign, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_data()
            lst = self.app.campaign["characters"]
            for i,c in enumerate(lst):
                if c["id"] == updated["id"]: lst[i] = updated; break
            self.app.set_dirty(True); self.refresh()

    def _delete(self, eid):
        self.app.campaign["characters"] = [
            c for c in self.app.campaign["characters"] if c["id"] != eid]
        self.app.set_dirty(True); self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: SESSIONS
# ══════════════════════════════════════════════════════════════════════════════
