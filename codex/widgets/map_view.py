"""
map_view.py — Multi-map panel with preset support.

MapView       — pan/zoom/calibrate/measure QGraphicsView (unchanged).
MapPanel      — multi-map manager: selector, add/rename/delete maps,
                preset loader, per-map calibration and measurements.

Each map is stored as a dict in campaign["maps"]:
  { id, name, path, pixels_per_unit, unit_name, measurements[] }

Preset calibrations live in codex/assets/map_presets.json and are
offered when adding a new map whose filename matches a known preset.
"""

from __future__ import annotations
import json
import math
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QFileDialog, QMessageBox,
    QGraphicsView, QGraphicsScene, QInputDialog, QColorDialog,
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor, QPen, QPixmap, QPainter, QFont, QShortcut, QKeySequence

from codex.theme import C, btn, lbl, sep_v
from codex.models import new_map_entry

# ── Preset loader ─────────────────────────────────────────────────────────────

def _load_presets() -> list[dict]:
    preset_path = Path(__file__).parent.parent / "assets" / "map_presets.json"
    try:
        with open(preset_path, "r", encoding="utf-8") as f:
            return json.load(f).get("presets", [])
    except Exception:
        return []

def _find_preset(filename: str) -> dict | None:
    """Return preset calibration if filename matches a known preset."""
    name = Path(filename).name.lower()
    for p in _load_presets():
        if p.get("filename", "").lower() == name:
            return p
    return None


# ── MapView (unchanged core) ──────────────────────────────────────────────────

class MapView(QGraphicsView):
    def __init__(self, status_cb=None, parent=None):
        super().__init__(parent)
        self.status_cb = status_cb or (lambda msg: None)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet(f"background:{C['bg_deep']};border:none;")

        self.mode = "pan"
        self.zoom_factor = 1.0
        self.calib_start = self.calib_end = self.calibration_line = None
        self.pixels_per_unit = None
        self.unit_name = "miles"
        self.measure_start = self.temp_line = None
        self.measurements: list[dict] = []
        self.current_color = QColor(239, 68, 68)
        self.color_presets = {
            "Crimson": QColor(239, 68, 68), "Gold": QColor(201, 147, 58),
            "Blue":    QColor(56, 189, 248), "Green": QColor(74, 222, 128),
            "Purple":  QColor(148, 0, 211),  "Orange": QColor(255, 165, 0),
        }
        self.is_panning = False
        self.pan_start = None

    def wheelEvent(self, event):
        try:
            mp = event.position().toPoint()
        except Exception:
            mp = event.pos()
        old = self.mapToScene(mp)
        f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.zoom_factor *= f
        self.scale(f, f)
        delta = self.mapToScene(mp) - old
        self.centerOn(self.mapToScene(self.viewport().rect().center()) - delta)
        event.accept()

    def mousePressEvent(self, event):
        sp = self.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "pan":
                self.is_panning = True; self.pan_start = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif self.mode == "calibrate":
                if self.calib_start is None:
                    self.calib_start = sp
                    self.status_cb("Click the second calibration point")
                else:
                    self.calib_end = sp; self._draw_calib_line(); self._calib_done()
            elif self.mode == "measure":
                if self.measure_start is None:
                    self.measure_start = sp; self.status_cb("Click end point")
                else:
                    self._complete_measure(sp)
        elif event.button() == Qt.MouseButton.RightButton:
            self._cancel()
        event.accept()

    def mouseMoveEvent(self, event):
        sp = self.mapToScene(event.pos())
        if self.mode == "pan" and self.is_panning:
            d = event.pos() - self.pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            self.pan_start = event.pos()
        elif self.mode == "calibrate" and self.calib_start and not self.calib_end:
            self._update_temp(self.calib_start, sp, QColor(74, 222, 128))
        elif self.mode == "measure" and self.measure_start:
            self._update_temp(self.measure_start, sp, self.current_color)
            if self.pixels_per_unit:
                d = math.dist((sp.x(), sp.y()),
                              (self.measure_start.x(), self.measure_start.y()))
                self.status_cb(
                    f"Distance: {d / self.pixels_per_unit:.2f} {self.unit_name}  (click to place)")
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.mode == "pan":
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        event.accept()

    def _update_temp(self, s, e, color):
        if self.temp_line: self.scene().removeItem(self.temp_line)
        pc = QColor(color); pc.setAlpha(180)
        pen = QPen(pc, 3); pen.setStyle(Qt.PenStyle.DashLine)
        self.temp_line = self.scene().addLine(s.x(), s.y(), e.x(), e.y(), pen)

    def _draw_calib_line(self):
        if self.calibration_line: self.scene().removeItem(self.calibration_line)
        pen = QPen(QColor(74, 222, 128), 4)
        self.calibration_line = self.scene().addLine(
            self.calib_start.x(), self.calib_start.y(),
            self.calib_end.x(), self.calib_end.y(), pen)

    def _calib_done(self):
        if hasattr(self.parent(), "_on_calib_points_set"):
            self.parent()._on_calib_points_set()

    def _complete_measure(self, end):
        if not self.pixels_per_unit:
            QMessageBox.warning(self, "Not calibrated", "Calibrate the scale first.")
            self._cancel(); return
        if self.temp_line: self.scene().removeItem(self.temp_line); self.temp_line = None
        px = math.dist((end.x(), end.y()),
                       (self.measure_start.x(), self.measure_start.y()))
        dist = px / self.pixels_per_unit
        pen = QPen(self.current_color, 3)
        line = self.scene().addLine(
            self.measure_start.x(), self.measure_start.y(), end.x(), end.y(), pen)
        mx = (self.measure_start.x() + end.x()) / 2
        my = (self.measure_start.y() + end.y()) / 2
        txt = self.scene().addText(f"{dist:.1f} {self.unit_name}")
        txt.setDefaultTextColor(self.current_color)
        f = QFont(); f.setPointSize(11); f.setBold(True); txt.setFont(f)
        txt.setPos(mx - 30, my - 32)
        self.measurements.append({
            "start":    (self.measure_start.x(), self.measure_start.y()),
            "end":      (end.x(), end.y()),
            "distance": dist,
            "color":    self.current_color.name(),
            "line": line, "text": txt,
        })
        self.measure_start = None
        self.status_cb(
            f"Measured {dist:.2f} {self.unit_name} · {len(self.measurements)} total")

    def _cancel(self):
        if self.temp_line: self.scene().removeItem(self.temp_line); self.temp_line = None
        self.measure_start = None; self.is_panning = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def clear_measurements(self):
        for m in self.measurements:
            if m.get("line"): self.scene().removeItem(m["line"])
            if m.get("text"): self.scene().removeItem(m["text"])
        self.measurements.clear(); self._cancel()

    def undo_last(self) -> bool:
        if not self.measurements: return False
        m = self.measurements.pop()
        if m.get("line"): self.scene().removeItem(m["line"])
        if m.get("text"): self.scene().removeItem(m["text"])
        return True

    def get_data(self) -> dict:
        return {
            "calibration": {
                "pixels_per_unit": self.pixels_per_unit,
                "unit_name": self.unit_name,
            },
            "measurements": [
                {"start": m["start"], "end": m["end"],
                 "distance": m["distance"], "color": m["color"]}
                for m in self.measurements
            ],
        }

    def load_data(self, data: dict):
        """Load calibration + measurements from a map entry or legacy JSON."""
        self.clear_measurements()
        # Support both new flat format and legacy {"calibration": {...}} format
        if "calibration" in data:
            self.pixels_per_unit = data["calibration"].get("pixels_per_unit")
            self.unit_name       = data["calibration"].get("unit_name", "miles")
        else:
            self.pixels_per_unit = data.get("pixels_per_unit")
            self.unit_name       = data.get("unit_name", "miles")

        for md in data.get("measurements", []):
            s = QPointF(*md["start"]); e = QPointF(*md["end"])
            color = QColor(md.get("color", "#ef4444"))
            pen = QPen(color, 3)
            line = self.scene().addLine(s.x(), s.y(), e.x(), e.y(), pen)
            mx, my = (s.x() + e.x()) / 2, (s.y() + e.y()) / 2
            txt = self.scene().addText(f"{md['distance']:.1f} {self.unit_name}")
            txt.setDefaultTextColor(color)
            f = QFont(); f.setPointSize(11); f.setBold(True); txt.setFont(f)
            txt.setPos(mx - 30, my - 32)
            self.measurements.append({**md, "line": line, "text": txt})


# ── MapPanel — multi-map manager ──────────────────────────────────────────────

class MapPanel(QWidget):
    """
    Manages multiple maps per campaign.
    Top bar: map selector dropdown + add/rename/delete.
    Main area: MapView for the active map.
    Bottom bar: calibrate / measure / color / undo / clear / fit controls.
    """

    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app    = app_ref
        self._scene = QGraphicsScene()
        self._active_map_id: str | None = None

        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        # ── Map selector bar ──────────────────────────────────────────────
        sel_bar = QWidget()
        sel_bar.setStyleSheet(
            f"background:{C['bg_panel']};border-bottom:1px solid {C['border']};")
        sl = QHBoxLayout(sel_bar); sl.setContentsMargins(10, 6, 10, 6); sl.setSpacing(8)
        sl.addWidget(lbl("MAP", C['text_dim'], 10, True, 1))

        self._map_combo = QComboBox()
        self._map_combo.setMinimumWidth(200)
        self._map_combo.setStyleSheet(
            f"background:{C['bg_input']};border:1px solid {C['border']};"
            f"border-radius:4px;color:{C['text_primary']};padding:4px 8px;font-size:12px;")
        self._map_combo.currentIndexChanged.connect(self._on_map_selected)
        sl.addWidget(self._map_combo, 1)

        add_btn    = btn("+ Add Map",  "icon"); add_btn.clicked.connect(self._add_map)
        rename_btn = btn("Rename",     "icon"); rename_btn.clicked.connect(self._rename_map)
        del_btn    = btn("🗑",          "danger"); del_btn.clicked.connect(self._delete_map)
        del_btn.setFixedWidth(32)
        sl.addWidget(add_btn); sl.addWidget(rename_btn); sl.addWidget(del_btn)
        vl.addWidget(sel_bar)

        # ── Status bar ────────────────────────────────────────────────────
        self._status = QLabel("Add a map to get started.")
        self._status.setStyleSheet(
            f"background:{C['bg_panel']};color:{C['text_muted']};"
            f"padding:4px 12px;font-size:11px;border-top:1px solid {C['border']};")

        # ── MapView ───────────────────────────────────────────────────────
        self.view = MapView(status_cb=lambda m: self._status.setText(m), parent=self)
        self.view.setScene(self._scene)
        vl.addWidget(self.view, 1)

        # ── Control bar ───────────────────────────────────────────────────
        ctrl = QWidget()
        ctrl.setStyleSheet(f"background:{C['bg_panel']};border-top:1px solid {C['border']};")
        cl = QHBoxLayout(ctrl); cl.setContentsMargins(10, 6, 10, 6); cl.setSpacing(8)

        _input_css = (f"background:{C['bg_input']};border:1px solid {C['border']};"
                      f"border-radius:4px;color:{C['text_primary']};padding:4px 8px;font-size:11px;")

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Map image path…")
        self._path_edit.setStyleSheet(
            f"background:{C['bg_input']};border:1px solid {C['border']};"
            f"border-radius:4px;color:{C['text_muted']};padding:4px 8px;font-size:11px;")
        cl.addWidget(self._path_edit, 1)

        browse = btn("Browse…", "icon"); browse.clicked.connect(self._browse_map)
        load   = btn("Load",    "icon"); load.clicked.connect(lambda: self._load_map())
        cl.addWidget(browse); cl.addWidget(load)
        cl.addWidget(sep_v())

        self._pan_btn   = btn("🖐 Pan",       "icon")
        self._calib_btn = btn("⚖ Calibrate", "icon")
        self._meas_btn  = btn("📏 Measure",   "icon")
        self._pan_btn.clicked.connect(lambda:   self._set_mode("pan"))
        self._calib_btn.clicked.connect(self._start_calib)
        self._meas_btn.clicked.connect(lambda:  self._set_mode("measure"))
        self._meas_btn.setEnabled(False)
        cl.addWidget(self._pan_btn); cl.addWidget(self._calib_btn); cl.addWidget(self._meas_btn)
        cl.addWidget(sep_v())

        self._dist_edit = QLineEdit(); self._dist_edit.setPlaceholderText("Distance")
        self._dist_edit.setMaximumWidth(90); self._dist_edit.setStyleSheet(_input_css)
        self._unit_edit = QLineEdit("miles"); self._unit_edit.setMaximumWidth(70)
        self._unit_edit.setStyleSheet(_input_css)
        self._set_calib_btn = btn("✓ Set", "icon")
        self._set_calib_btn.setEnabled(False)
        self._set_calib_btn.clicked.connect(self._set_calib)
        cl.addWidget(self._dist_edit); cl.addWidget(self._unit_edit)
        cl.addWidget(self._set_calib_btn)
        cl.addWidget(sep_v())

        self._color_combo = QComboBox()
        self._color_combo.addItems(list(self.view.color_presets.keys()))
        self._color_combo.setMaximumWidth(90)
        self._color_combo.currentTextChanged.connect(self._change_color)
        self._color_combo.setStyleSheet(
            f"background:{C['bg_input']};border:1px solid {C['border']};"
            f"border-radius:4px;color:{C['text_primary']};padding:2px 6px;font-size:11px;")
        self._color_btn = QPushButton("🎨"); self._color_btn.setMaximumWidth(34)
        self._color_btn.setStyleSheet(
            f"background:#ef4444;border:2px solid {C['border']};border-radius:4px;font-size:14px;")
        self._color_btn.clicked.connect(self._pick_color)
        cl.addWidget(self._color_combo); cl.addWidget(self._color_btn)
        cl.addWidget(sep_v())

        undo = btn("↶",             "icon"); undo.clicked.connect(self._undo)
        clr  = btn("🗑 Clear",      "icon"); clr.clicked.connect(self._clear)
        fit  = btn("⬜ Fit",        "icon"); fit.clicked.connect(self._fit)
        imp  = btn("📂 Import JSON","icon"); imp.clicked.connect(self._import_old_json)
        imp.setToolTip("Import measurements from a standalone MapMeasurer JSON file")
        cl.addWidget(undo); cl.addWidget(clr); cl.addWidget(fit); cl.addWidget(imp)

        self._count_lbl = QLabel("0 measurements")
        self._count_lbl.setStyleSheet(f"color:{C['text_dim']};font-size:11px;")
        cl.addWidget(self._count_lbl)

        vl.addWidget(ctrl)
        vl.addWidget(self._status)

        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._undo)

        # Populate selector from campaign
        self._refresh_combo(select_id=None)

    # ── Map selector ──────────────────────────────────────────────────────────

    def _refresh_combo(self, select_id: str | None = None):
        """Rebuild the map dropdown from campaign["maps"]."""
        self._map_combo.blockSignals(True)
        self._map_combo.clear()
        maps = self.app.campaign.get("maps", [])
        for m in maps:
            self._map_combo.addItem(m["name"], userData=m["id"])
        self._map_combo.blockSignals(False)

        if not maps:
            self._active_map_id = None
            return

        # Select by id if given, else first map
        idx = 0
        if select_id:
            for i, m in enumerate(maps):
                if m["id"] == select_id:
                    idx = i; break
        self._map_combo.setCurrentIndex(idx)
        self._load_active_map()

    def _on_map_selected(self, index: int):
        if index < 0: return
        # Save current map state before switching
        self._save_active_map()
        mid = self._map_combo.itemData(index)
        self._active_map_id = mid
        self._load_active_map()

    def _active_map(self) -> dict | None:
        if not self._active_map_id: return None
        for m in self.app.campaign.get("maps", []):
            if m["id"] == self._active_map_id:
                return m
        return None

    # ── Add / rename / delete ─────────────────────────────────────────────────

    def _add_map(self):
        """Browse for an image, auto-apply preset calibration if known, add to campaign."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Map Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp);;All Files (*)")
        if not path: return

        # Check for a preset calibration
        preset = _find_preset(path)
        if preset:
            reply = QMessageBox.question(
                self, "Preset Found",
                f"This looks like '{preset['name']}'.\n"
                f"Apply the preset calibration "
                f"({preset['calibration']['pixels_per_unit']:.4f} "
                f"px/{preset['calibration']['unit_name']})?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                entry = new_map_entry(
                    name=preset["name"], path=path,
                    pixels_per_unit=preset["calibration"]["pixels_per_unit"],
                    unit_name=preset["calibration"]["unit_name"])
            else:
                name, ok = QInputDialog.getText(self, "Map Name", "Name for this map:",
                                                text=Path(path).stem)
                if not ok or not name.strip(): return
                entry = new_map_entry(name=name.strip(), path=path)
        else:
            name, ok = QInputDialog.getText(self, "Map Name", "Name for this map:",
                                            text=Path(path).stem)
            if not ok or not name.strip(): return
            entry = new_map_entry(name=name.strip(), path=path)

        self._save_active_map()
        self.app.campaign.setdefault("maps", []).append(entry)
        self.app.set_dirty(True)
        self._refresh_combo(select_id=entry["id"])

    def _rename_map(self):
        m = self._active_map()
        if not m: return
        name, ok = QInputDialog.getText(self, "Rename Map", "New name:", text=m["name"])
        if ok and name.strip():
            m["name"] = name.strip()
            self.app.set_dirty(True)
            self._refresh_combo(select_id=m["id"])

    def _delete_map(self):
        m = self._active_map()
        if not m: return
        if QMessageBox.question(
            self, "Delete Map",
            f"Delete '{m['name']}' and all its measurements?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self.app.campaign["maps"] = [
            x for x in self.app.campaign.get("maps", []) if x["id"] != m["id"]]
        self._scene.clear()
        self.view.measurements.clear()
        self.app.set_dirty(True)
        self._refresh_combo()

    # ── Load / save active map ────────────────────────────────────────────────

    def _load_active_map(self):
        """Load the currently selected map entry into the view."""
        m = self._active_map()
        if not m:
            self._status.setText("No map selected.")
            return

        self._path_edit.setText(m.get("path", ""))
        self._unit_edit.setText(m.get("unit_name", "miles"))

        # Load image
        path = m.get("path", "")
        if path:
            self._load_map(restore=True, map_entry=m)
        else:
            self._scene.clear()
            self.view.measurements.clear()
            self._status.setText(f"{m['name']} — no image loaded yet. Browse to select one.")

        # Restore calibration
        self.view.pixels_per_unit = m.get("pixels_per_unit")
        self.view.unit_name       = m.get("unit_name", "miles")
        self._meas_btn.setEnabled(bool(self.view.pixels_per_unit))
        self._count_lbl.setText(f"{len(self.view.measurements)} measurements")

    def _save_active_map(self):
        """Write current view state back into the active map entry."""
        m = self._active_map()
        if not m: return
        data = self.view.get_data()
        m["pixels_per_unit"] = data["calibration"]["pixels_per_unit"]
        m["unit_name"]       = data["calibration"]["unit_name"]
        m["measurements"]    = data["measurements"]

    def get_map_data(self) -> dict:
        """Called by app._write — saves active map then returns full maps list."""
        self._save_active_map()
        return {}   # maps list is already in campaign["maps"]

    def load_map_data(self, data: dict):
        """Legacy: import old standalone JSON into the active map."""
        m = self._active_map()
        if not m: return
        self.view.load_data(data)
        m["pixels_per_unit"] = self.view.pixels_per_unit
        m["unit_name"]       = self.view.unit_name
        m["measurements"]    = self.view.get_data()["measurements"]
        self._meas_btn.setEnabled(bool(self.view.pixels_per_unit))
        self._count_lbl.setText(f"{len(self.view.measurements)} measurements")
        self.app.set_dirty(True)

    # ── Control bar actions ───────────────────────────────────────────────────

    def _set_mode(self, mode):
        self.view.mode = mode; self.view._cancel()
        cursors = {"pan": Qt.CursorShape.OpenHandCursor,
                   "measure": Qt.CursorShape.CrossCursor,
                   "calibrate": Qt.CursorShape.CrossCursor}
        self.view.setCursor(cursors.get(mode, Qt.CursorShape.ArrowCursor))
        msgs = {"pan": "Pan: drag to move",
                "measure": "Measure: click two points",
                "calibrate": "Calibrate: click first point on scale"}
        self._status.setText(msgs.get(mode, ""))

    def _browse_map(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Map Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp);;All Files (*)")
        if p: self._path_edit.setText(p)

    def _load_map(self, restore: bool = False, map_entry: dict | None = None):
        path = self._path_edit.text().strip()
        if not path: return
        pix = QPixmap(path)
        if pix.isNull():
            QMessageBox.warning(self, "Map Error", f"Could not load image:\n{path}"); return
        self._scene.clear()
        self._scene.addPixmap(pix)
        self._scene.setSceneRect(QRectF(pix.rect()))
        if not restore:
            self.view.measurements.clear()

        # Reload measurements from map entry if restoring
        if restore and map_entry and map_entry.get("measurements"):
            self.view.load_data(map_entry)

        self._fit()

        # Update active map path
        m = self._active_map()
        if m:
            m["path"] = path
            self.app.set_dirty(True)

        self._status.setText(
            f"{m['name'] if m else 'Map'} — {pix.width()}×{pix.height()}px"
            + ("" if restore else "  ·  calibrate the scale to start measuring"))

    def _import_old_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Map Measurement JSON", "",
            "JSON Files (*.json);;All Files (*)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "measurements" not in data and "calibration" not in data:
                QMessageBox.warning(self, "Import Error",
                    "This doesn't look like a map measurement file."); return
            self.load_map_data(data)
            self._status.setText(f"Imported {len(self.view.measurements)} measurements")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not read file:\n{e}")

    def _start_calib(self):
        self.view.calib_start = self.view.calib_end = None
        self._set_mode("calibrate"); self._set_calib_btn.setEnabled(False)

    def _on_calib_points_set(self):
        self._set_calib_btn.setEnabled(True)
        self._status.setText("Points set — enter the real distance and click ✓ Set")

    def _set_calib(self):
        txt = self._dist_edit.text().strip()
        if not txt: QMessageBox.warning(self, "Error", "Enter a distance value first."); return
        try:
            dist = float(txt)
            px = math.dist(
                (self.view.calib_end.x(), self.view.calib_end.y()),
                (self.view.calib_start.x(), self.view.calib_start.y()))
            self.view.pixels_per_unit = px / dist
            self.view.unit_name = self._unit_edit.text().strip() or "units"
            # Save calibration into active map entry immediately
            m = self._active_map()
            if m:
                m["pixels_per_unit"] = self.view.pixels_per_unit
                m["unit_name"]       = self.view.unit_name
                self.app.set_dirty(True)
            self._set_calib_btn.setEnabled(False); self._meas_btn.setEnabled(True)
            self._set_mode("pan")
            self._status.setText(
                f"Calibrated: {dist} {self.view.unit_name} = {px:.0f}px  ·  ready to measure")
        except (ValueError, AttributeError):
            QMessageBox.warning(self, "Error", "Invalid distance or calibration points not set.")

    def _change_color(self, name):
        if name in self.view.color_presets:
            self.view.current_color = self.view.color_presets[name]
            self._color_btn.setStyleSheet(
                f"background:{self.view.current_color.name()};"
                f"border:2px solid {C['border']};border-radius:4px;font-size:14px;")

    def _pick_color(self):
        col = QColorDialog.getColor(self.view.current_color, self)
        if col.isValid():
            self.view.current_color = col
            self._color_btn.setStyleSheet(
                f"background:{col.name()};border:2px solid {C['border']};"
                f"border-radius:4px;font-size:14px;")
            self._color_combo.setCurrentIndex(-1)

    def _undo(self):
        if self.view.undo_last():
            self._count_lbl.setText(f"{len(self.view.measurements)} measurements")
            self._status.setText("Undone last measurement")

    def _clear(self):
        if not self.view.measurements: return
        if QMessageBox.question(self, "Clear", "Clear all measurements?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes:
            self.view.clear_measurements()
            self._count_lbl.setText("0 measurements")

    def _fit(self):
        self.view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def refresh(self):
        """Called when a campaign is loaded — repopulate the map selector."""
        self._refresh_combo(select_id=None)