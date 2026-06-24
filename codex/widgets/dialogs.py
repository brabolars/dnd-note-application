"""
dialogs.py — Edit dialogs for every entry type.
Each dialog inherits _BaseDialog and adds its own form fields.
"""

from __future__ import annotations
from datetime import datetime
from PyQt6.QtWidgets import QLineEdit, QTextEdit, QComboBox, QGridLayout, QTabWidget, QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal

from codex.theme import C, field_lbl
from codex.models import new_character, new_session, new_lore, new_location
from codex.widgets.common import _BaseDialog


class CharacterDialog(_BaseDialog):
    deleted = pyqtSignal(str)

    def __init__(self, data=None, campaign=None, parent=None):
        d = data or new_character(); d["_type"] = "character"
        super().__init__("Edit Character" if data else "New Character",
                         d, campaign or {}, parent)
        f = self._form
        g = QGridLayout(); g.setSpacing(10)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)

        self.name_e = QLineEdit(d.get("name", "")); self.name_e.setPlaceholderText("Name…")
        g.addWidget(field_lbl("NAME"), 0, 0, 1, 4); g.addWidget(self.name_e, 1, 0, 1, 4)

        self.race_e  = QLineEdit(d.get("race", ""));         self.race_e.setPlaceholderText("Human, Elf…")
        self.class_e = QLineEdit(d.get("class_or_job", "")); self.class_e.setPlaceholderText("Wizard, Merchant…")
        g.addWidget(field_lbl("RACE"), 2, 0);     g.addWidget(self.race_e,  3, 0)
        g.addWidget(field_lbl("CLASS / JOB"), 2, 2); g.addWidget(self.class_e, 3, 2)

        self.role_c   = QComboBox(); self.role_c.addItems(["NPC","Ally","Enemy","Neutral","Player"])
        self.role_c.setCurrentText(d.get("role", "NPC"))
        self.status_c = QComboBox(); self.status_c.addItems(["Alive","Dead","Unknown","Missing"])
        self.status_c.setCurrentText(d.get("status", "Alive"))
        g.addWidget(field_lbl("ROLE"),   4, 0); g.addWidget(self.role_c,   5, 0)
        g.addWidget(field_lbl("STATUS"), 4, 2); g.addWidget(self.status_c, 5, 2)

        self.first_e = QLineEdit(d.get("first_seen", "")); self.first_e.setPlaceholderText("Session or date…")
        g.addWidget(field_lbl("FIRST SEEN"), 6, 0, 1, 4); g.addWidget(self.first_e, 7, 0, 1, 4)
        f.addLayout(g)

        f.addWidget(field_lbl("NOTES"))
        self.notes_e = QTextEdit(d.get("notes", ""))
        self.notes_e.setPlaceholderText("Personality, secrets, relationships…")
        f.addWidget(self.notes_e, 1)

    def get_data(self):
        d = dict(self._data); d.pop("_type", None)
        d["name"]        = self.name_e.text().strip() or "Unknown"
        d["race"]        = self.race_e.text().strip()
        d["class_or_job"]= self.class_e.text().strip()
        d["role"]        = self.role_c.currentText()
        d["status"]      = self.status_c.currentText()
        d["first_seen"]  = self.first_e.text().strip()
        d["notes"]       = self.notes_e.toPlainText().strip()
        d["linked"]      = self._links
        return d


class SessionDialog(_BaseDialog):
    deleted = pyqtSignal(str)

    def __init__(self, data=None, campaign=None, parent=None):
        d = data or new_session(); d["_type"] = "session"
        super().__init__("Edit Session" if data else "Log New Session",
                         d, campaign or {}, parent)
        f = self._form
        g = QGridLayout(); g.setSpacing(10); g.setColumnStretch(0, 3)

        self.name_e = QLineEdit(d.get("name", "")); self.name_e.setPlaceholderText("Session name…")
        self.date_e = QLineEdit(d.get("date", datetime.now().strftime("%Y-%m-%d")))
        self.date_e.setPlaceholderText("YYYY-MM-DD"); self.date_e.setMaximumWidth(130)
        g.addWidget(field_lbl("SESSION NAME"), 0, 0); g.addWidget(self.name_e, 1, 0)
        g.addWidget(field_lbl("DATE"), 0, 2);         g.addWidget(self.date_e, 1, 2)
        f.addLayout(g)

        f.addWidget(field_lbl("SUMMARY"))
        self.summary_e = QTextEdit(d.get("summary", ""))
        self.summary_e.setPlaceholderText("Key plot beats…")
        self.summary_e.setMaximumHeight(90); f.addWidget(self.summary_e)

        f.addWidget(field_lbl("DETAILED NOTES"))
        self.notes_e = QTextEdit(d.get("notes", ""))
        self.notes_e.setPlaceholderText("Everything else…")
        f.addWidget(self.notes_e, 1)

    def get_data(self):
        d = dict(self._data); d.pop("_type", None)
        d["name"]    = self.name_e.text().strip() or f"Session {d.get('date','')}"
        d["date"]    = self.date_e.text().strip()
        d["summary"] = self.summary_e.toPlainText().strip()
        d["notes"]   = self.notes_e.toPlainText().strip()
        d["linked"]  = self._links
        return d


class LoreDialog(_BaseDialog):
    deleted = pyqtSignal(str)

    def __init__(self, data=None, campaign=None, parent=None):
        d = data or new_lore(); d["_type"] = "lore"
        super().__init__("Edit Lore" if data else "New Lore Entry",
                         d, campaign or {}, parent)
        f = self._form
        g = QGridLayout(); g.setSpacing(10); g.setColumnStretch(0, 3)

        self.title_e = QLineEdit(d.get("title", "")); self.title_e.setPlaceholderText("Title…")
        self.cat_c   = QComboBox()
        self.cat_c.addItems(["World","Faction","Item","Place","Prophecy","History","Other"])
        self.cat_c.setCurrentText(d.get("category", "World")); self.cat_c.setMaximumWidth(120)
        g.addWidget(field_lbl("TITLE"), 0, 0);    g.addWidget(self.title_e, 1, 0)
        g.addWidget(field_lbl("CATEGORY"), 0, 2); g.addWidget(self.cat_c,   1, 2)
        f.addLayout(g)

        f.addWidget(field_lbl("CONTENT"))
        self.content_e = QTextEdit(d.get("content", ""))
        self.content_e.setPlaceholderText("Everything known…")
        f.addWidget(self.content_e, 1)

    def get_data(self):
        d = dict(self._data); d.pop("_type", None)
        d["title"]    = self.title_e.text().strip() or "Untitled"
        d["category"] = self.cat_c.currentText()
        d["content"]  = self.content_e.toPlainText().strip()
        d["linked"]   = self._links
        return d


class LocationDialog(_BaseDialog):
    deleted = pyqtSignal(str)

    def __init__(self, data=None, campaign=None, parent_id="", parent=None):
        d = data or new_location(parent_id=parent_id); d["_type"] = "location"
        super().__init__("Edit Location" if data else "New Location",
                         d, campaign or {}, parent)
        self.setMinimumSize(600, 640)
        f = self._form
        g = QGridLayout(); g.setSpacing(10)
        g.setColumnStretch(0, 2); g.setColumnStretch(2, 1); g.setColumnStretch(4, 1)

        self.name_e = QLineEdit(d.get("name", "")); self.name_e.setPlaceholderText("Location name…")
        g.addWidget(field_lbl("NAME"), 0, 0, 1, 5); g.addWidget(self.name_e, 1, 0, 1, 5)

        self.type_c   = QComboBox()
        self.type_c.addItems(["City","Town","Village","Dungeon","Tavern","Temple",
                               "Wilderness","Ruin","Region","Fortress","Other"])
        self.type_c.setCurrentText(d.get("type", "City"))
        self.status_c = QComboBox()
        self.status_c.addItems(["Unknown","Safe","Hostile","Contested","Visited","Destroyed"])
        self.status_c.setCurrentText(d.get("status", "Unknown"))
        self.faction_e = QLineEdit(d.get("faction", "")); self.faction_e.setPlaceholderText("Controlling faction…")
        g.addWidget(field_lbl("TYPE"),    2, 0); g.addWidget(self.type_c,    3, 0)
        g.addWidget(field_lbl("STATUS"),  2, 2); g.addWidget(self.status_c,  3, 2)
        g.addWidget(field_lbl("FACTION"), 2, 4); g.addWidget(self.faction_e, 3, 4)
        f.addLayout(g)

        tabs = QTabWidget(); f.addWidget(tabs, 1)

        nw = QWidget(); nl = QVBoxLayout(nw); nl.setContentsMargins(8, 8, 8, 8)
        self.notes_e = QTextEdit(d.get("notes", ""))
        self.notes_e.setPlaceholderText("General description, atmosphere…")
        nl.addWidget(self.notes_e)
        tabs.addTab(nw, "Notes")

        sw = QWidget(); sl = QVBoxLayout(sw); sl.setContentsMargins(8, 8, 8, 8)
        sl.addWidget(field_lbl("SECRETS / HIDDEN INFO"))
        self.secrets_e = QTextEdit(d.get("secrets", ""))
        self.secrets_e.setPlaceholderText("Things the players don't know yet…")
        self.secrets_e.setMinimumHeight(80); sl.addWidget(self.secrets_e)
        sl.addWidget(field_lbl("LOOT / ITEMS OF INTEREST"))
        self.loot_e = QTextEdit(d.get("loot", ""))
        sl.addWidget(self.loot_e)
        tabs.addTab(sw, "Secrets & Loot")

    def get_data(self):
        d = dict(self._data); d.pop("_type", None)
        d["name"]    = self.name_e.text().strip() or "Unknown"
        d["type"]    = self.type_c.currentText()
        d["status"]  = self.status_c.currentText()
        d["faction"] = self.faction_e.text().strip()
        d["notes"]   = self.notes_e.toPlainText().strip()
        d["secrets"] = self.secrets_e.toPlainText().strip()
        d["loot"]    = self.loot_e.toPlainText().strip()
        d["linked"]  = self._links
        return d
