"""
locations.py — LocationsPage panel.
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
from codex.widgets.map_view import MapPanel
LOC_STATUS_COL = {
    "Safe":      C['green'],
    "Hostile":   C['red_text'],
    "Contested": C['yellow'],
    "Unknown":   C['text_muted'],
    "Visited":   C['sky'],
    "Destroyed": C['text_dim'],
}
LOC_TYPE_ICON = {
    "City": "🏙", "Town": "🏘", "Village": "🏡",
    "Dungeon": "⛏", "Tavern": "🍺", "Temple": "⛪",
    "Wilderness": "🌲", "Ruin": "🏚", "Region": "🗺",
    "Fortress": "🏰", "Other": "📍",
}

class LocationsPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent); self.app = app; self._selected_id = None
        self._build()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Left: tree ──
        left = QWidget(); left.setFixedWidth(260)
        left.setStyleSheet(f"background:{C['bg_panel']};border-right:1px solid {C['border']};")
        ll = QVBoxLayout(left); ll.setContentsMargins(12,14,12,12); ll.setSpacing(8)

        ll.addWidget(lbl("LOCATIONS", C['text_dim'], 11, True, 2))

        btn_row = QHBoxLayout()
        add_top = btn("+ Region",   "icon"); add_top.clicked.connect(lambda: self._add_loc(""))
        btn_row.addWidget(add_top); btn_row.addStretch(); ll.addLayout(btn_row)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(18)
        self._tree.itemSelectionChanged.connect(self._on_select)
        ll.addWidget(self._tree, 1)

        root.addWidget(left)

        # ── Right: tabs ──
        right = QWidget(); rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)

        self._tabs = QTabWidget()
        self._detail_tab = self._build_detail_tab()
        self._map_panel  = MapPanel(self.app)
        self._tabs.addTab(self._detail_tab, "📋 Detail")
        self._tabs.addTab(self._map_panel,  "🗺 Map")
        rl.addWidget(self._tabs)
        root.addWidget(right, 1)

        self.refresh()

    def _build_detail_tab(self):
        w = QWidget(); vl = QVBoxLayout(w)
        vl.setContentsMargins(24,20,24,20); vl.setSpacing(12)

        # Header row
        hr = QHBoxLayout()
        self._det_name  = lbl("Select a location", C['parchment'], 18, True)
        self._det_badge = QLabel(); self._det_badge.setStyleSheet(
            f"color:{C['text_muted']};font-size:11px;")
        hr.addWidget(self._det_name); hr.addStretch(); hr.addWidget(self._det_badge)
        vl.addLayout(hr)

        # Action buttons
        ar = QHBoxLayout()
        self._add_child_btn = btn("+ Add Sub-location","icon")
        self._add_child_btn.clicked.connect(self._add_child)
        self._add_child_btn.setEnabled(False)
        self._edit_btn = btn("Edit","icon"); self._edit_btn.clicked.connect(self._edit)
        self._edit_btn.setEnabled(False)
        ar.addWidget(self._add_child_btn); ar.addWidget(self._edit_btn); ar.addStretch()
        vl.addLayout(ar)
        vl.addWidget(sep_h())

        # Info grid
        self._det_grid = QGridLayout(); self._det_grid.setSpacing(10)
        self._det_grid.setColumnStretch(1,1); self._det_grid.setColumnStretch(3,1)
        vl.addLayout(self._det_grid)
        vl.addWidget(sep_h())

        # Notes display
        self._det_notes = QLabel(); self._det_notes.setWordWrap(True)
        self._det_notes.setStyleSheet(f"color:{C['text_primary']};font-size:12px;")
        vl.addWidget(self._det_notes)

        # Secrets
        self._det_secrets_lbl = lbl("SECRETS", C['crimson_glow'], 10, True, 1)
        self._det_secrets_lbl.hide()
        self._det_secrets = QLabel(); self._det_secrets.setWordWrap(True)
        self._det_secrets.setStyleSheet(f"color:{C['red_text']};font-size:12px;")
        vl.addWidget(self._det_secrets_lbl); vl.addWidget(self._det_secrets)

        # Loot
        self._det_loot_lbl = lbl("LOOT", C['gold'], 10, True, 1)
        self._det_loot_lbl.hide()
        self._det_loot = QLabel(); self._det_loot.setWordWrap(True)
        self._det_loot.setStyleSheet(f"color:{C['gold']};font-size:12px;")
        vl.addWidget(self._det_loot_lbl); vl.addWidget(self._det_loot)

        # Links
        vl.addWidget(sep_h())
        self._det_links = QLabel(); self._det_links.setWordWrap(True)
        self._det_links.setStyleSheet(f"color:{C['blue']};font-size:11px;")
        vl.addWidget(self._det_links)
        vl.addStretch()

        self._empty_det = EmptyState("🗺","No location selected",
            "Pick a location from the tree, or add one.")
        vl.addWidget(self._empty_det)
        return w

    def _populate_det(self, loc):
        # Clear grid
        for i in reversed(range(self._det_grid.count())):
            it = self._det_grid.takeAt(i)
            if it.widget(): it.widget().deleteLater()

        self._det_name.setText(LOC_TYPE_ICON.get(loc.get("type","Other"),"📍") + "  " + loc.get("name","?"))
        status = loc.get("status","Unknown")
        self._det_badge.setText(f"  {status}  ")
        self._det_badge.setStyleSheet(
            f"color:{LOC_STATUS_COL.get(status,C['text_muted'])};"
            f"font-size:11px;font-weight:600;")

        for col, (label, val) in enumerate([
            ("TYPE",    loc.get("type","")),
            ("FACTION", loc.get("faction","—") or "—"),
        ]):
            self._det_grid.addWidget(_fieldlbl(label), 0, col*2)
            self._det_grid.addWidget(lbl(val, C['text_primary'], 12), 1, col*2)

        self._det_notes.setText(loc.get("notes","") or "No notes yet.")
        s = loc.get("secrets","")
        self._det_secrets_lbl.setVisible(bool(s))
        self._det_secrets.setText(s)
        lo = loc.get("loot","")
        self._det_loot_lbl.setVisible(bool(lo))
        self._det_loot.setText(lo)
        links = loc.get("linked",[])
        self._det_links.setText("🔗 " + "  ·  ".join(l["label"] for l in links) if links else "")
        self._empty_det.hide()
        self._add_child_btn.setEnabled(True); self._edit_btn.setEnabled(True)

    def refresh(self):
        self._tree.clear()
        locs = self.app.campaign.get("locations", [])
        top_items = {}

        def make_item(loc):
            icon = LOC_TYPE_ICON.get(loc.get("type","Other"),"📍")
            status = loc.get("status","Unknown")
            col = LOC_STATUS_COL.get(status, C['text_muted'])
            item = QTreeWidgetItem([f"{icon}  {loc['name']}"])
            item.setData(0, Qt.ItemDataRole.UserRole, loc["id"])
            item.setForeground(0, QColor(C['text_primary']))
            item.setToolTip(0, f"{loc.get('type','')} · {status}")
            return item

        # Build top-level
        for loc in locs:
            if not loc.get("parent_id"):
                item = make_item(loc)
                self._tree.addTopLevelItem(item)
                top_items[loc["id"]] = item

        # Build children
        for loc in locs:
            pid = loc.get("parent_id","")
            if pid and pid in top_items:
                item = make_item(loc)
                top_items[pid].addChild(item)
                top_items[loc["id"]] = item  # support deeper nesting

        self._tree.expandAll()

        # Restore selection
        if self._selected_id:
            self._select_by_id(self._selected_id)

        # Refresh map panel (repopulates map selector on file open)
        self._map_panel.refresh()

    def _select_by_id(self, eid):
        it = self._tree.invisibleRootItem()
        def search(node):
            for i in range(node.childCount()):
                child = node.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) == eid:
                    self._tree.setCurrentItem(child); return True
                if search(child): return True
            return False
        search(it)

    def _on_select(self):
        items = self._tree.selectedItems()
        if not items: return
        eid = items[0].data(0, Qt.ItemDataRole.UserRole)
        self._selected_id = eid
        loc = next((l for l in self.app.campaign.get("locations",[]) if l["id"]==eid), None)
        if loc: self._populate_det(loc)

    def _get_selected_loc(self):
        if not self._selected_id: return None
        return next((l for l in self.app.campaign.get("locations",[])
                     if l["id"] == self._selected_id), None)

    def _add_loc(self, parent_id):
        dlg = LocationDialog(campaign=self.app.campaign, parent_id=parent_id, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.app.campaign["locations"].append(dlg.get_data())
            self.app.set_dirty(True); self.refresh()

    def _add_child(self):
        if self._selected_id: self._add_loc(self._selected_id)

    def _edit(self):
        loc = self._get_selected_loc()
        if not loc: return
        dlg = LocationDialog(data=loc, campaign=self.app.campaign, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_data()
            lst = self.app.campaign["locations"]
            for i,l in enumerate(lst):
                if l["id"] == updated["id"]: lst[i] = updated; break
            self.app.set_dirty(True); self._selected_id = updated["id"]; self.refresh()
            self._populate_det(updated)

    def _delete(self, eid):
        # Also delete children
        to_del = {eid}
        changed = True
        while changed:
            changed = False
            for l in self.app.campaign.get("locations",[]):
                if l.get("parent_id") in to_del and l["id"] not in to_del:
                    to_del.add(l["id"]); changed = True
        self.app.campaign["locations"] = [
            l for l in self.app.campaign["locations"] if l["id"] not in to_del]
        self._selected_id = None; self.app.set_dirty(True); self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: LORE
# ══════════════════════════════════════════════════════════════════════════════