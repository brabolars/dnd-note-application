"""
common.py — Small reusable widgets used across multiple pages.
EmptyState, TagBadge, LinkPicker, _BaseDialog (base for all edit dialogs).
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QScrollArea, QCheckBox, QTabWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from codex.theme import C, btn, lbl, sep_h


class EmptyState(QWidget):
    def __init__(self, icon: str, title: str, sub: str, parent=None):
        super().__init__(parent)
        vl = QVBoxLayout(self)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.setSpacing(8)
        for text, css in [
            (icon,  f"font-size:38px;color:{C['text_dim']};"),
            (title, f"font-size:15px;font-weight:600;color:{C['text_muted']};"),
            (sub,   f"font-size:12px;color:{C['text_dim']};"),
        ]:
            l = QLabel(text)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet(css)
            l.setWordWrap(True)
            vl.addWidget(l)


class TagBadge(QLabel):
    _ROLES = {
        "NPC":     (C["blue_bg"],   C["blue"]),
        "Ally":    (C["sky_bg"],    C["sky"]),
        "Enemy":   (C["red_bg"],    C["red_text"]),
        "Neutral": (C["yellow_bg"], C["yellow"]),
        "Player":  (C["green_bg"],  C["green"]),
    }

    def __init__(self, text: str, role: str | None = None, parent=None):
        super().__init__(text, parent)
        bg, fg = self._ROLES.get(role, (C["bg_hover"], C["text_muted"]))
        self.setStyleSheet(
            f"background:{bg};color:{fg};border-radius:3px;"
            f"padding:2px 7px;font-size:10px;font-weight:600;"
        )


class LinkPicker(QDialog):
    """Tabbed dialog to pick cross-links from any entry type."""

    def __init__(self, campaign: dict, current_links: list,
                 exclude_type: str | None = None, exclude_id: str | None = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Links")
        self.setMinimumSize(480, 500)
        from codex.theme import SS
        self.setStyleSheet(SS)
        self.result_links = list(current_links)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(16, 16, 16, 16)
        vl.setSpacing(10)
        vl.addWidget(lbl("Link this entry to:", C['parchment'], 14, True))

        tabs = QTabWidget()
        vl.addWidget(tabs, 1)

        sections = [
            ("🎭 Characters", "character", campaign.get("characters", [])),
            ("📜 Sessions",   "session",   campaign.get("sessions",   [])),
            ("🗺 Locations",  "location",  campaign.get("locations",  [])),
            ("📖 Lore",       "lore",      campaign.get("lore",       [])),
        ]
        for tab_title, etype, entries in sections:
            if exclude_type == etype:
                entries = [e for e in entries if e["id"] != exclude_id]
            w = QWidget(); tl = QVBoxLayout(w); tl.setContentsMargins(8, 8, 8, 8)
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            inner = QWidget(); il = QVBoxLayout(inner); il.setSpacing(4)
            for entry in entries:
                label = entry.get("name") or entry.get("title") or "Unnamed"
                cb = QCheckBox(label)
                cb.setChecked(any(l["id"] == entry["id"] for l in self.result_links))
                cb.stateChanged.connect(
                    lambda state, e=entry, t=etype: self._toggle(state, e, t))
                il.addWidget(cb)
            il.addStretch()
            scroll.setWidget(inner); tl.addWidget(scroll)
            tabs.addTab(w, tab_title)

        row = QHBoxLayout()
        ok = btn("Done", "primary"); ok.clicked.connect(self.accept)
        cancel = btn("Cancel", "secondary"); cancel.clicked.connect(self.reject)
        row.addStretch(); row.addWidget(cancel); row.addWidget(ok)
        vl.addLayout(row)

    def _toggle(self, state, entry, etype):
        label = entry.get("name") or entry.get("title") or "Unnamed"
        if state == Qt.CheckState.Checked.value:
            if not any(l["id"] == entry["id"] for l in self.result_links):
                self.result_links.append({"type": etype, "id": entry["id"], "label": label})
        else:
            self.result_links = [l for l in self.result_links if l["id"] != entry["id"]]


class _BaseDialog(QDialog):
    """Shared scaffold for all edit dialogs: title, delete, links, ok/cancel."""
    deleted = pyqtSignal(str)

    def __init__(self, title_text: str, data: dict, campaign: dict, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 560)
        from codex.theme import SS
        self.setStyleSheet(SS)
        self._data     = dict(data)
        self._campaign = campaign
        self._links    = list(data.get("linked", []))

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(lbl(title_text, C['parchment'], 16, True))
        top.addStretch()
        if data.get("id"):
            del_btn = btn("Delete", "danger")
            del_btn.clicked.connect(self._delete)
            top.addWidget(del_btn)
        root.addLayout(top)
        root.addWidget(sep_h())

        self._form = QVBoxLayout()
        root.addLayout(self._form, 1)

        root.addWidget(sep_h())
        link_row = QHBoxLayout()
        link_row.addWidget(lbl("LINKS:", C['text_dim'], 11))
        self._link_display = QLabel()
        self._link_display.setWordWrap(True)
        self._link_display.setStyleSheet(f"color:{C['text_muted']};font-size:11px;")
        link_row.addWidget(self._link_display, 1)
        manage = btn("Manage Links…", "icon")
        manage.clicked.connect(self._open_links)
        link_row.addWidget(manage)
        root.addLayout(link_row)
        self._refresh_link_display()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = btn("Cancel", "secondary"); cancel.clicked.connect(self.reject)
        save   = btn("Save",   "primary");   save.clicked.connect(self.accept)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _refresh_link_display(self):
        if self._links:
            self._link_display.setText("  ·  ".join(l["label"] for l in self._links))
        else:
            self._link_display.setText("None")

    def _open_links(self):
        dlg = LinkPicker(
            self._campaign, self._links,
            exclude_type=self._data.get("_type"),
            exclude_id=self._data.get("id"),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._links = dlg.result_links
            self._refresh_link_display()

    def _delete(self):
        if QMessageBox.question(
            self, "Delete", "Delete this entry? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.deleted.emit(self._data["id"])
            self.reject()

    def get_data(self) -> dict:
        raise NotImplementedError
