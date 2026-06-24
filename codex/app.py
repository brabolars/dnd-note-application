"""
app.py — MainWindow: sidebar, page stack, file I/O.
"""

from __future__ import annotations
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette

from codex import __version__
from codex.theme import C, SS, btn, lbl, sep_h, ThemeManager, build_ss
from codex.models import new_campaign, migrate
from codex.pages import (
    OverviewPage, CharactersPage, SessionsPage,
    LocationsPage, LorePage, ConnectionsPage,
)
from codex.pages.settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Codex — D&D Campaign Tracker")
        self.setMinimumSize(1100, 720)
        self.campaign = new_campaign()
        self._dirty = False
        self._current_file = None
        # Apply saved theme before building UI
        ThemeManager.instance().apply()
        self._build_ui()
        self.setStyleSheet(build_ss(C))

    def _apply_theme(self):
        """Re-apply the active theme to the whole window."""
        from codex.theme import build_ss, C
        self.setStyleSheet(build_ss(C))

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget(); sidebar.setObjectName("sidebar")
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(0,0,0,0); sl.setSpacing(0)

        t = QLabel("CODEX"); t.setObjectName("app_title"); sl.addWidget(t)
        s = QLabel("CAMPAIGN TRACKER"); s.setObjectName("app_subtitle"); sl.addWidget(s)
        cl = QLabel("CAMPAIGN"); cl.setObjectName("campaign_label"); sl.addWidget(cl)
        self.campaign_label = QLabel("Unnamed Campaign")
        self.campaign_label.setObjectName("campaign_name")
        self.campaign_label.setWordWrap(True); sl.addWidget(self.campaign_label)

        self._nav_btns = []
        nav = [
            ("Overview",     0),
            ("Characters",   1),
            ("Sessions",     2),
            ("Locations",    3),
            ("Lore",         4),
            ("Connections",  5),
            ("Settings",     6),
        ]
        for label, idx in nav:
            b = QPushButton(label); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, i=idx: self._nav(i))
            self._nav_btns.append(b); sl.addWidget(b)

        sl.addStretch()
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{C['border']};"); sl.addWidget(sep)

        for label, cb, style in [
            ("New Campaign", self._new_campaign, "secondary"),
            ("Open…",        self._open_file,    "secondary"),
            ("Save",         self._save_file,    "gold"),
            ("Save As…",     self._save_as_file, "secondary"),
        ]:
            b = btn(label, style); b.clicked.connect(cb)
            b.setStyleSheet(b.styleSheet() + "QPushButton{margin:0 12px;}")
            sl.addWidget(b)
        sl.setContentsMargins(0,0,0,10)
        root.addWidget(sidebar)

        # ── Stack ──
        self.stack = QStackedWidget()
        self._pages = [
            OverviewPage(self),
            CharactersPage(self),
            SessionsPage(self),
            LocationsPage(self),
            LorePage(self),
            ConnectionsPage(self),
            SettingsPage(self),
        ]
        for p in self._pages: self.stack.addWidget(p)
        root.addWidget(self.stack)
        self._nav(0)

    def _nav_btn_style(self, active):
        if active:
            return (f"QPushButton{{background:{C['bg_card']};border:none;"
                    f"border-left:3px solid {C['crimson']};color:{C['crimson_glow']};"
                    f"text-align:left;padding:10px 20px;font-size:13px;font-weight:600;}}")
        return (f"QPushButton{{background:transparent;border:none;"
                f"border-left:3px solid transparent;color:{C['text_muted']};"
                f"text-align:left;padding:10px 20px;font-size:13px;}}"
                f"QPushButton:hover{{background:{C['bg_hover']};color:{C['text_primary']};}}")

    def _nav(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self._nav_btns):
            b.setStyleSheet(self._nav_btn_style(i == idx))
        self._pages[idx].refresh()

    def update_campaign_label(self):
        name = self.campaign["meta"].get("name","Unnamed Campaign")
        self.campaign_label.setText(name)
        self.setWindowTitle(f"D&D Campaign Tracker — {name}{' •' if self._dirty else ''}")

    def set_dirty(self, d):
        self._dirty = d; self.update_campaign_label()

    # ── File ops ──
    def _new_campaign(self):
        if self._dirty and not self._confirm_discard(): return
        self.campaign = new_campaign(); self._current_file = None
        self._dirty = False; self.update_campaign_label()
        for p in self._pages: p.refresh()
        self._nav(0)

    def _open_file(self):
        if self._dirty and not self._confirm_discard(): return
        path, _ = QFileDialog.getOpenFileName(
            self,"Open Campaign","",
            "D&D Campaign (*.dndbook);;JSON Files (*.json);;All Files (*)")
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                data = json.load(f)
            self.campaign = migrate(data)
            self._current_file = path; self._dirty = False
            self.update_campaign_label()
            for p in self._pages: p.refresh()
            self._nav(0)
        except Exception as e:
            QMessageBox.critical(self,"Error",f"Could not open file:\n{e}")

    def _save_file(self):
        if not self._current_file: self._save_as_file(); return
        self._write(self._current_file)

    def _save_as_file(self):
        name = self.campaign["meta"].get("name","campaign").replace(" ","_")
        path, _ = QFileDialog.getSaveFileName(
            self,"Save Campaign",f"{name}.dndbook",
            "D&D Campaign (*.dndbook);;JSON Files (*.json);;All Files (*)")
        if not path: return
        if not (path.endswith(".dndbook") or path.endswith(".json")):
            path += ".dndbook"
        self._current_file = path; self._write(path)

    def _write(self, path):
        try:
            self.campaign["meta"]["modified"] = datetime.now().isoformat()
            # Flush active map state (measurements + calibration) into campaign["maps"]
            loc_page = self._pages[3]
            loc_page._map_panel.get_map_data()   # triggers _save_active_map internally
            # Snapshot graph annotations + positions
            conn_page = self._pages[5]
            conn_page.save_annotations()

            # Atomic write: temp file → rename over original
            import os
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.campaign, f, indent=2, ensure_ascii=False)
            backup = path + ".bak"
            if os.path.exists(path):
                os.replace(path, backup)
            os.replace(tmp, path)
            self._dirty = False; self.update_campaign_label()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save:\n{e}")

    def _confirm_discard(self):
        return QMessageBox.question(
            self,"Unsaved Changes","You have unsaved changes. Continue anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        if self._dirty:
            r = QMessageBox.question(
                self,"Unsaved Changes","Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Save:
                self._save_file(); event.accept()
            elif r == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("D&D Campaign Tracker")
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(C["bg_deep"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(C["text_primary"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(C["bg_input"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(C["text_primary"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(C["bg_panel"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text_primary"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(C["crimson"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(pal)
    w = MainWindow(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


def run():
    """Entry point registered in pyproject.toml."""
    import sys
    app = QApplication(sys.argv)
    app.setApplicationName("Codex")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(C["bg_deep"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(C["text_primary"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(C["bg_input"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(C["text_primary"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(C["bg_panel"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text_primary"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(C["crimson"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(pal)

    w = MainWindow(); w.show()
    sys.exit(app.exec())