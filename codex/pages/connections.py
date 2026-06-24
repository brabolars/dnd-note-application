"""
connections.py — Focused radial graph.

Left panel: searchable subject picker (all characters, locations, lore).
Right panel: radial graph centred on the selected subject.
  Ring 0 — the selected hub
  Ring 1 — entries directly linked to the hub
  Ring 2 — entries linked to ring-1 nodes but not the hub
  Ring 3 — everything else in the campaign (faded, outer band)

Manual annotation lines (draw mode) are visual-only and saved in the
campaign's graph_annotations list.
"""

from __future__ import annotations
import math
import random
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsLineItem, QGraphicsItem, QColorDialog,
    QLineEdit, QScrollArea, QSizePolicy, QSlider,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QPainter, QFont

from codex.theme import C, btn, lbl, sep_h, sep_v

# ── Display constants ─────────────────────────────────────────────────────────

TYPE_ICON = {"character": "🎭", "location": "🗺", "lore": "📖"}
TYPE_COL  = {
    "character": C['blue'],
    "location":  C['green'],
    "lore":      C['sky'],
}
TYPE_COL_DIM = {
    "character": C['blue_bg'],
    "location":  C['green_bg'],
    "lore":      C['sky_bg'],
}

RING_R       = [0, 200, 370, 530]
RING_DIM     = [1.0, 1.0, 0.75, 0.45]
NODE_R_HUB   = 56
NODE_R_R1    = 40
NODE_R_R2    = 32
NODE_R_OUTER = 22


# ── Graph primitives ──────────────────────────────────────────────────────────

class AnnotationLine(QGraphicsLineItem):
    """Visual-only dashed line drawn manually between two nodes."""

    def __init__(self, na, nb, color: str, ann_id: str, parent=None):
        super().__init__(parent)
        self.na     = na
        self.nb     = nb
        self.ann_id = ann_id
        self._color = color
        pen = QPen(QColor(color), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 4])
        self.setPen(pen)
        self.setZValue(1.5)
        self.setAcceptHoverEvents(True)
        self._sync()

    def _sync(self):
        self.setLine(self.na.x(), self.na.y(), self.nb.x(), self.nb.y())

    def sync(self):
        self._sync()

    def hoverEnterEvent(self, event):
        pen = self.pen(); pen.setWidth(3); self.setPen(pen)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        pen = self.pen(); pen.setWidth(2); self.setPen(pen)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)


class MindNode(QGraphicsEllipseItem):
    """Draggable node; propagates moves to attached edge lines."""

    def __init__(self, entry: dict, etype: str, radius: int, ring: int,
                 ring_dim: float = 1.0):
        self.entry   = entry
        self.etype   = etype
        self.ring    = ring
        self.is_hub  = (ring == 0)
        r = radius
        super().__init__(-r, -r, r * 2, r * 2)
        self.radius        = r
        self._dragging     = False
        self._struct_edges: list = []
        self._annot_edges:  list = []

        dim = ring_dim

        if self.is_hub:
            fill   = QColor(C['crimson_dim'])
            border = QColor(C['crimson_glow'])
            bw = 3
        else:
            fill   = QColor(TYPE_COL_DIM.get(etype, C['bg_card']))
            border = QColor(TYPE_COL.get(etype, C['border']))
            fill.setAlphaF(dim)
            border.setAlphaF(max(0.3, dim))
            bw = 2

        self.setBrush(fill)
        self.setPen(QPen(border, bw))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

        label   = entry.get("name") or entry.get("title") or "?"
        icon    = TYPE_ICON.get(etype, "•")
        short   = label[:13] + ("…" if len(label) > 13 else "")
        display = f"{icon}\n{short}"

        txt = QGraphicsTextItem(display, self)
        fsize = 8 if self.is_hub else max(5, 8 - ring)
        font  = QFont("Segoe UI", fsize)
        font.setBold(ring <= 1)
        txt.setFont(font)
        col = QColor(C['crimson_glow'] if self.is_hub
                     else TYPE_COL.get(etype, C['text_primary']))
        col.setAlphaF(max(0.4, dim))
        txt.setDefaultTextColor(col)
        txt.setTextWidth(r * 1.9)
        br = txt.boundingRect()
        txt.setPos(-br.width() / 2, -br.height() / 2)

    def hoverEnterEvent(self, event):
        pen = self.pen(); pen.setWidth(pen.width() + 1); self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        pen = self.pen(); pen.setWidth(max(1, pen.width() - 1)); self.setPen(pen)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self._dragging = True
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge, other, src in self._struct_edges:
                if src: edge.setLine(self.x(), self.y(), other.x(), other.y())
                else:   edge.setLine(other.x(), other.y(), self.x(), self.y())
            for ann in self._annot_edges:
                ann.sync()
        return super().itemChange(change, value)

    def register_struct_edge(self, line, other, is_source: bool):
        self._struct_edges.append((line, other, is_source))

    def register_annot_edge(self, ann):
        self._annot_edges.append(ann)

    def unregister_annot_edge(self, ann):
        self._annot_edges = [a for a in self._annot_edges if a is not ann]


# ── Mind-map view ─────────────────────────────────────────────────────────────

class MindMapView(QGraphicsView):
    node_selected = pyqtSignal(object)   # MindNode
    annot_deleted = pyqtSignal(str)      # ann_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet(f"background:{C['bg_deep']};border:none;")
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._nodes:  list = []
        self._annots: list = []
        self._selected     = None
        self._mode         = "pan"
        self._draw_first   = None
        self._draw_color   = C['crimson_glow']
        self._temp_line    = None
        # Always NoDrag — we handle panning manually so nodes always win
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._panning    = False
        self._pan_origin = None

    # ── public ───────────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        self._mode = mode
        self._draw_first = None
        if self._temp_line:
            self._scene.removeItem(self._temp_line)
            self._temp_line = None
        self.setCursor(Qt.CursorShape.CrossCursor if mode == "draw"
                       else Qt.CursorShape.ArrowCursor)

    def set_draw_color(self, color_hex: str):
        self._draw_color = color_hex

    def fit(self):
        self.fitInView(
            self._scene.itemsBoundingRect().adjusted(-60, -60, 60, 60),
            Qt.AspectRatioMode.KeepAspectRatio)

    def get_annotations(self) -> list:
        return [
            {"id": a.ann_id, "from_id": a.na.entry["id"],
             "to_id": a.nb.entry["id"], "color": a._color}
            for a in self._annots
        ]

    def get_positions(self, hub_id: str) -> dict:
        """Return {hub_id: {entry_id: [x, y]}} scoped to this hub's layout."""
        return {n.entry["id"]: [n.x(), n.y()] for n in self._nodes}

    def load_annotations(self, ann_list: list, node_map: dict):
        for d in ann_list:
            fid = d.get("from_id"); tid = d.get("to_id")
            if fid not in node_map or tid not in node_map: continue
            na = node_map[fid]; nb = node_map[tid]
            ann = AnnotationLine(na, nb, d.get("color", C['crimson_glow']), d["id"])
            self._scene.addItem(ann)
            self._annots.append(ann)
            na.register_annot_edge(ann)
            nb.register_annot_edge(ann)

    # ── events ────────────────────────────────────────────────────────────────

    def wheelEvent(self, event):
        f = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        self.scale(f, f); event.accept()

    def _is_pan_trigger(self, event) -> bool:
        """Middle-mouse OR Ctrl+left = pan."""
        if event.button() == Qt.MouseButton.MiddleButton:
            return True
        if (event.button() == Qt.MouseButton.LeftButton and
                event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            return True
        return False

    def mousePressEvent(self, event):
        # ── Pan trigger (middle-mouse or Ctrl+left) ──────────────────────
        if self._is_pan_trigger(event):
            self._panning    = True
            self._pan_origin = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept(); return

        # ── Right-click: delete annotation ───────────────────────────────
        if event.button() == Qt.MouseButton.RightButton:
            ann = self._hit_annot(event.pos())
            if ann:
                self._delete_annot(ann); event.accept(); return
            self._cancel_draw(); event.accept(); return

        # ── Left-click ────────────────────────────────────────────────────
        if event.button() == Qt.MouseButton.LeftButton:
            item = self._hit_node(event.pos())

            if self._mode == "draw":
                if item:
                    if self._draw_first is None:
                        self._draw_first = item; self._highlight(item, True)
                    elif item is not self._draw_first:
                        self._finish_draw(item)
                    else:
                        self._cancel_draw()
                else:
                    self._cancel_draw()
                event.accept(); return

            # Pan mode — node drag or select
            if item:
                self._select(item)
                # Pass to scene so the item's own mousePressEvent fires
                # (enabling ItemIsMovable drag). Do NOT call event.accept()
                # here so Qt propagates to the item.
                super().mousePressEvent(event)
            else:
                self._select(None)
                event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Manual pan
        if self._panning and self._pan_origin is not None:
            delta      = event.pos() - self._pan_origin
            self._pan_origin = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            event.accept(); return

        # Draw mode preview line
        if self._mode == "draw" and self._draw_first:
            sp = self.mapToScene(event.pos())
            if self._temp_line: self._scene.removeItem(self._temp_line)
            pen = QPen(QColor(self._draw_color), 2)
            pen.setStyle(Qt.PenStyle.DashLine); pen.setDashPattern([6, 4])
            self._temp_line = self._scene.addLine(
                self._draw_first.x(), self._draw_first.y(), sp.x(), sp.y(), pen)
            self._temp_line.setZValue(10)
            event.accept(); return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning and event.button() in (
                Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            self._panning    = False
            self._pan_origin = None
            self.setCursor(Qt.CursorShape.CrossCursor if self._mode == "draw"
                           else Qt.CursorShape.ArrowCursor)
            event.accept(); return
        super().mouseReleaseEvent(event)

    # ── internals ─────────────────────────────────────────────────────────────

    def _hit_node(self, vpos):
        item = self.itemAt(vpos)
        while item and not isinstance(item, MindNode):
            item = item.parentItem()
        return item if isinstance(item, MindNode) else None

    def _hit_annot(self, vpos):
        for item in self.items(vpos):
            if isinstance(item, AnnotationLine): return item
        return None

    def _highlight(self, node, on: bool):
        if on:
            bright = QColor(TYPE_COL.get(node.etype, C['border']))
            bright.setAlpha(140); node.setBrush(bright)
        else:
            dim = RING_DIM[min(node.ring, len(RING_DIM) - 1)]
            if node.is_hub:
                node.setBrush(QColor(C['crimson_dim']))
            else:
                fill = QColor(TYPE_COL_DIM.get(node.etype, C['bg_card']))
                fill.setAlphaF(dim); node.setBrush(fill)

    def _select(self, node):
        if self._selected: self._highlight(self._selected, False)
        self._selected = node
        if node:
            self._highlight(node, True)
            self.node_selected.emit(node)

    def _finish_draw(self, nb):
        na = self._draw_first
        if self._temp_line:
            self._scene.removeItem(self._temp_line); self._temp_line = None
        self._highlight(na, False); self._draw_first = None
        pair = tuple(sorted([na.entry["id"], nb.entry["id"]]))
        for ex in self._annots:
            if tuple(sorted([ex.na.entry["id"], ex.nb.entry["id"]])) == pair: return
        ann = AnnotationLine(na, nb, self._draw_color,
                             datetime.now().strftime("%Y%m%d%H%M%S%f"))
        self._scene.addItem(ann); self._annots.append(ann)
        na.register_annot_edge(ann); nb.register_annot_edge(ann)

    def _cancel_draw(self):
        if self._draw_first: self._highlight(self._draw_first, False)
        self._draw_first = None
        if self._temp_line:
            self._scene.removeItem(self._temp_line); self._temp_line = None

    def _delete_annot(self, ann):
        ann.na.unregister_annot_edge(ann); ann.nb.unregister_annot_edge(ann)
        self._annots = [a for a in self._annots if a is not ann]
        self._scene.removeItem(ann); self.annot_deleted.emit(ann.ann_id)

    # ── graph build ───────────────────────────────────────────────────────────

    def build_graph(self, campaign: dict, hub_id: str,
                    saved_annotations: list | None = None,
                    saved_positions:   dict | None = None,
                    max_rings:         int         = 4) -> dict:
        """
        Draw a radial graph centred on hub_id.
        max_rings controls BFS depth:
          - 1 = hub only
          - 2 = hub + direct links
          - N = hub + N-1 degrees of separation
          - anything unreachable lands on the outermost ring (always shown, faded)
        """
        self._scene.clear()
        self._nodes.clear(); self._annots.clear()
        self._selected = self._draw_first = None
        self._temp_line = None

        # Collect all entries
        all_entries: list[tuple[str, dict]] = []
        for etype, key, nk in [
            ("character", "characters", "name"),
            ("location",  "locations",  "name"),
            ("lore",      "lore",       "title"),
        ]:
            for e in campaign.get(key, []):
                all_entries.append((etype, e))

        if not all_entries:
            return {}

        # Build undirected adjacency
        adj: dict[str, set] = {e["id"]: set() for _, e in all_entries}
        for _, e in all_entries:
            for lnk in e.get("linked", []):
                lid = lnk.get("id")
                if lid in adj:
                    adj[e["id"]].add(lid)
                    adj[lid].add(e["id"])

        # BFS ring assignment — depth up to (max_rings - 1) hops
        # Ring max_rings = "overflow" / unreachable, always shown faded
        overflow_ring = max_rings
        ring_of: dict[str, int] = {e["id"]: overflow_ring for _, e in all_entries}
        if hub_id in ring_of:
            ring_of[hub_id] = 0
            frontier = [hub_id]
            for ring_num in range(1, max_rings):
                nf = []
                for nid in frontier:
                    for nbr in adj.get(nid, []):
                        if ring_of[nbr] == overflow_ring:
                            ring_of[nbr] = ring_num; nf.append(nbr)
                frontier = nf
                if not frontier:
                    break  # graph exhausted before max_rings

        # Dynamic ring geometry — evenly spaced, scales with max_rings
        base_spacing = 180
        ring_radii = [0] + [base_spacing * i for i in range(1, max_rings + 1)]
        # Dim factor per ring: hub = full, each subsequent ring fades a bit
        ring_dims = [max(0.35, 1.0 - 0.12 * r) for r in range(max_rings + 1)]

        # ── Scene decoration ──────────────────────────────────────────────
        grid_extent = ring_radii[-1] + 400
        step = max(80, grid_extent // 22)
        for gx in range(-grid_extent, grid_extent + 1, step):
            for gy in range(-grid_extent, grid_extent + 1, step):
                dot = self._scene.addEllipse(gx - 1, gy - 1, 2, 2)
                dot.setBrush(QColor(C['border']))
                dot.setPen(QPen(Qt.PenStyle.NoPen))
                dot.setZValue(0)

        for r_px in ring_radii[1:]:
            circle = self._scene.addEllipse(-r_px, -r_px, r_px * 2, r_px * 2)
            pen = QPen(QColor(C['border'])); pen.setStyle(Qt.PenStyle.DotLine)
            circle.setPen(pen); circle.setBrush(Qt.GlobalColor.transparent)
            circle.setZValue(0.5)

        # ── Place nodes ───────────────────────────────────────────────────
        random.seed(hash(hub_id) & 0xFFFF)
        node_map: dict[str, MindNode] = {}
        by_ring: dict[int, list] = {r: [] for r in range(max_rings + 1)}
        for etype, e in all_entries:
            by_ring[ring_of[e["id"]]].append((etype, e))

        # Node radii shrink slightly per ring
        def node_radius(ring: int) -> int:
            return max(18, NODE_R_HUB - ring * 8)

        for ring_num, ring_entries in by_ring.items():
            n    = len(ring_entries)
            r_px = ring_radii[min(ring_num, len(ring_radii) - 1)]
            for i, (etype, e) in enumerate(ring_entries):
                node = MindNode(e, etype,
                                radius=node_radius(ring_num),
                                ring=ring_num,
                                ring_dim=ring_dims[min(ring_num, len(ring_dims) - 1)])
                if ring_num == 0:
                    nx, ny = 0.0, 0.0
                else:
                    angle = 2 * math.pi * i / max(n, 1) + random.uniform(-0.04, 0.04)
                    nx = r_px * math.cos(angle)
                    ny = r_px * math.sin(angle)
                node.setPos(nx, ny)
                self._scene.addItem(node)
                self._nodes.append(node)
                node_map[e["id"]] = node

        # ── Restore saved positions ───────────────────────────────────────
        if saved_positions:
            for nid, pos in saved_positions.items():
                if nid in node_map:
                    node_map[nid].setPos(pos[0], pos[1])

        # ── Structural edges ──────────────────────────────────────────────
        drawn_pairs: set = set()
        for _, e in all_entries:
            for lnk in e.get("linked", []):
                lid = lnk.get("id")
                if lid not in node_map: continue
                pair = tuple(sorted([e["id"], lid]))
                if pair in drawn_pairs: continue
                drawn_pairs.add(pair)
                na = node_map[e["id"]]; nb = node_map[lid]
                # Skip edges between two overflow nodes — too noisy
                if na.ring == overflow_ring and nb.ring == overflow_ring: continue
                worst_ring = min(max(na.ring, nb.ring), len(ring_dims) - 1)
                alpha = int(255 * ring_dims[worst_ring])
                col = QColor(C['border']); col.setAlpha(alpha)
                line = self._scene.addLine(na.x(), na.y(), nb.x(), nb.y(), QPen(col, 1))
                line.setZValue(1)
                na.register_struct_edge(line, nb, True)
                nb.register_struct_edge(line, na, False)

        # ── Restore annotations ───────────────────────────────────────────
        if saved_annotations:
            self.load_annotations(saved_annotations, node_map)

        self._scene.setSceneRect(
            self._scene.itemsBoundingRect().adjusted(-200, -200, 200, 200))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        return node_map


# ── Subject picker (left panel) ───────────────────────────────────────────────

class SubjectPicker(QWidget):
    """
    Searchable list of all entries.
    Emitting subject_selected(etype, entry) triggers a graph rebuild.
    """
    subject_selected = pyqtSignal(str, dict)   # etype, entry

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(
            f"background:{C['bg_panel']};border-right:1px solid {C['border']};")
        self._campaign: dict = {}
        self._selected_id: str | None = None

        vl = QVBoxLayout(self); vl.setContentsMargins(10, 12, 10, 10); vl.setSpacing(8)
        vl.addWidget(lbl("FOCUS ON", C['text_dim'], 10, True, 2))

        self._search = QLineEdit(); self._search.setPlaceholderText("Search…")
        self._search.textChanged.connect(self._rebuild_list)
        vl.addWidget(self._search)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_container = QWidget()
        self._list_layout    = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        vl.addWidget(scroll, 1)

    def set_campaign(self, campaign: dict):
        self._campaign = campaign
        self._rebuild_list()

    def _rebuild_list(self):
        # Clear existing rows (keep stretch)
        while self._list_layout.count() > 1:
            it = self._list_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        query = self._search.text().lower()
        sections = [
            ("character", "characters", "name"),
            ("location",  "locations",  "name"),
            ("lore",      "lore",       "title"),
        ]

        any_results = False
        for etype, key, nk in sections:
            entries = self._campaign.get(key, [])
            if query:
                entries = [e for e in entries
                           if query in (e.get(nk) or "").lower()]
            if not entries:
                continue
            any_results = True

            # Section header
            hdr = QLabel(etype.upper() + "S")
            hdr.setStyleSheet(
                f"color:{C['text_dim']};font-size:9px;letter-spacing:2px;"
                f"padding:6px 4px 2px 4px;font-weight:600;")
            self._list_layout.insertWidget(self._list_layout.count() - 1, hdr)

            for entry in entries:
                self._list_layout.insertWidget(
                    self._list_layout.count() - 1,
                    self._make_row(etype, entry, nk))

        if not any_results:
            ph = QLabel("No entries found")
            ph.setStyleSheet(f"color:{C['text_dim']};font-size:11px;padding:8px;")
            ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, ph)

    def _make_row(self, etype: str, entry: dict, nk: str) -> QPushButton:
        label = entry.get(nk) or "Unnamed"
        icon  = TYPE_ICON.get(etype, "•")
        col   = TYPE_COL.get(etype, C['text_muted'])
        is_selected = (entry["id"] == self._selected_id)

        row = QPushButton(f"{icon}  {label}")
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setToolTip(f"{etype.capitalize()}: {label}")

        link_count = len(entry.get("linked", []))
        base = (f"QPushButton{{text-align:left;padding:6px 8px;"
                f"border:none;border-radius:4px;font-size:11px;")
        if is_selected:
            row.setStyleSheet(base +
                f"background:{C['crimson_dim']};color:{C['parchment']};"
                f"font-weight:600;}}"
                f"QPushButton:hover{{background:{C['crimson_dim']};}}")
        else:
            row.setStyleSheet(base +
                f"background:transparent;color:{col};}}"
                f"QPushButton:hover{{background:{C['bg_hover']};"
                f"color:{C['text_primary']};}}")

        row.clicked.connect(lambda _, et=etype, en=entry: self._on_click(et, en))
        return row

    def _on_click(self, etype: str, entry: dict):
        self._selected_id = entry["id"]
        self._rebuild_list()
        self.subject_selected.emit(etype, entry)

    def select_first(self):
        """Auto-select the first entry if nothing is selected yet."""
        if self._selected_id:
            return
        for etype, key, nk in [
            ("character", "characters", "name"),
            ("location",  "locations",  "name"),
            ("lore",      "lore",       "title"),
        ]:
            entries = self._campaign.get(key, [])
            if entries:
                self._on_click(etype, entries[0])
                return


# ── Connections page ──────────────────────────────────────────────────────────

class ConnectionsPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app         = app
        self._draw_color = C['crimson_glow']
        self._hub_entry: dict | None  = None
        self._hub_etype: str          = ""
        self._build()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ── Left: subject picker ──────────────────────────────────────────
        self._picker = SubjectPicker()
        self._picker.subject_selected.connect(self._on_subject_selected)
        root.addWidget(self._picker)

        # ── Right: canvas + toolbar ───────────────────────────────────────
        canvas_wrap = QWidget()
        cvl = QVBoxLayout(canvas_wrap); cvl.setContentsMargins(0, 0, 0, 0); cvl.setSpacing(0)

        # Toolbar
        tb = QWidget()
        tb.setStyleSheet(f"background:{C['bg_panel']};border-bottom:1px solid {C['border']};")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(12, 7, 12, 7); tbl.setSpacing(8)

        self._hub_label = lbl("No subject selected", C['text_muted'], 12, True)
        tbl.addWidget(self._hub_label)
        tbl.addWidget(sep_v())

        # Mode buttons
        _active = (f"background:{C['crimson_dim']};border:1px solid {C['crimson']};"
                   f"border-radius:4px;color:{C['parchment']};padding:4px 10px;font-size:12px;")
        _idle   = (f"background:transparent;border:1px solid {C['border']};"
                   f"border-radius:4px;color:{C['text_muted']};padding:4px 10px;font-size:12px;")
        self._pan_btn  = btn("🖐 Pan",  "icon")
        self._draw_btn = btn("✏ Draw", "icon")
        self._pan_btn.clicked.connect(lambda: self._set_mode("pan"))
        self._draw_btn.clicked.connect(lambda: self._set_mode("draw"))
        self._pan_btn.setStyleSheet(_active)
        self._draw_btn.setStyleSheet(_idle)
        tbl.addWidget(self._pan_btn); tbl.addWidget(self._draw_btn)

        self._color_swatch = QPushButton()
        self._color_swatch.setFixedSize(22, 22)
        self._color_swatch.setToolTip("Annotation line colour")
        self._color_swatch.clicked.connect(self._pick_color)
        self._update_swatch()
        tbl.addWidget(self._color_swatch)

        tbl.addWidget(sep_v())
        tbl.addWidget(lbl("Right-click dashed line to delete", C['text_dim'], 10))
        tbl.addStretch()

        # Depth slider
        tbl.addWidget(lbl("DEPTH", C['text_dim'], 10, True, 1))
        self._depth_val_lbl = lbl("4", C['gold'], 11, True)
        tbl.addWidget(self._depth_val_lbl)
        self._depth_slider = QSlider(Qt.Orientation.Horizontal)
        self._depth_slider.setMinimum(1)
        self._depth_slider.setMaximum(10)
        self._depth_slider.setValue(4)
        self._depth_slider.setFixedWidth(100)
        self._depth_slider.setToolTip("Number of rings — how many degrees of separation to show")
        self._depth_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px; background: {C['border']}; border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px; height: 14px; margin: -5px 0;
                background: {C['gold']}; border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {C['gold_dim']}; border-radius: 2px;
            }}
        """)
        self._depth_slider.valueChanged.connect(self._depth_changed)
        tbl.addWidget(self._depth_slider)
        tbl.addWidget(sep_v())

        fit_btn = btn("⬜ Fit", "icon"); fit_btn.clicked.connect(lambda: self._map.fit())
        tbl.addWidget(fit_btn)
        tbl.addWidget(sep_v())

        for etype in ["character", "location", "lore"]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{TYPE_COL[etype]};font-size:13px;")
            tbl.addWidget(dot)
            tbl.addWidget(lbl(etype.capitalize(), TYPE_COL[etype], 10))

        cvl.addWidget(tb)

        # Canvas split: graph + detail panel
        canvas_body = QHBoxLayout(); canvas_body.setContentsMargins(0,0,0,0); canvas_body.setSpacing(0)

        self._map = MindMapView()
        self._map.node_selected.connect(self._on_node_selected)
        self._map.annot_deleted.connect(self._on_annot_deleted)
        canvas_body.addWidget(self._map, 1)

        # Detail panel
        self._detail = QWidget(); self._detail.setFixedWidth(250)
        self._detail.setStyleSheet(
            f"background:{C['bg_panel']};border-left:1px solid {C['border']};")
        dl = QVBoxLayout(self._detail); dl.setContentsMargins(14, 14, 14, 14); dl.setSpacing(8)

        self._d_title = lbl("", C['parchment'], 14, True)
        self._d_title.setWordWrap(True); dl.addWidget(self._d_title)
        self._d_type  = lbl("", C['text_muted'], 10, spacing=1); dl.addWidget(self._d_type)
        self._d_ring  = lbl("", C['text_dim'],   10);            dl.addWidget(self._d_ring)
        dl.addWidget(sep_h())
        self._d_body  = QLabel(); self._d_body.setWordWrap(True)
        self._d_body.setStyleSheet(f"color:{C['text_primary']};font-size:12px;")
        self._d_body.setAlignment(Qt.AlignmentFlag.AlignTop)
        dl.addWidget(self._d_body)
        dl.addWidget(sep_h())
        self._d_links_hdr = lbl("LINKED TO", C['text_dim'], 10, True, 1)
        dl.addWidget(self._d_links_hdr)
        self._d_links = QLabel(); self._d_links.setWordWrap(True)
        self._d_links.setStyleSheet(f"color:{C['text_muted']};font-size:11px;")
        dl.addWidget(self._d_links)
        dl.addStretch()

        hint = (
            "← Pick a subject to focus on\n\n"
            "🖐  Pan — drag/click to inspect\n"
            "✏  Draw — click A then B for\n"
            "    a visual annotation line\n\n"
            "Right-click dashed line removes it\n\n"
            "Rings:\n"
            "  ● Centre — your focus\n"
            "  ● Ring 1 — direct links\n"
            "  ● Ring 2 — second degree\n"
            "  ● Ring 3 — everything else"
        )
        self._d_hint = lbl(hint, C['text_dim'], 10)
        self._d_hint.setWordWrap(True); dl.addWidget(self._d_hint)

        canvas_body.addWidget(self._detail)
        cvl.addLayout(canvas_body, 1)
        root.addWidget(canvas_wrap, 1)

    # ── subject selection ─────────────────────────────────────────────────────

    def _on_subject_selected(self, etype: str, entry: dict):
        self._hub_entry = entry
        self._hub_etype = etype
        label = entry.get("name") or entry.get("title") or "?"
        self._hub_label.setText(
            f"{TYPE_ICON.get(etype, '•')}  {label}")
        self._hub_label.setStyleSheet(
            f"color:{TYPE_COL.get(etype, C['parchment'])};font-size:12px;font-weight:700;")
        self._d_title.setText("")
        self._d_type.setText(""); self._d_ring.setText("")
        self._d_body.setText(""); self._d_links.setText("")
        self._d_hint.show()
        self._rebuild_graph()

    # ── node click → detail panel ─────────────────────────────────────────────

    def _on_node_selected(self, node):
        e = node.entry; etype = node.etype
        label = e.get("name") or e.get("title") or "?"
        col   = TYPE_COL.get(etype, C['text_primary'])

        self._d_title.setText(f"{TYPE_ICON.get(etype, '•')}  {label}")
        self._d_title.setStyleSheet(
            f"color:{C['parchment']};font-size:14px;font-weight:700;")
        self._d_type.setText(f"{etype.upper()}{'  ★ Focus' if node.is_hub else ''}")
        self._d_type.setStyleSheet(
            f"color:{col};font-size:10px;letter-spacing:1px;font-weight:600;")
        self._d_ring.setText(
            ["Centre / Focus", "Ring 1 — direct link",
             "Ring 2 — second degree", "Ring 3 — peripheral"]
            [min(node.ring, 3)])

        lines = []
        if etype == "character":
            for k, v in [("Race", e.get("race","")),
                         ("Class", e.get("class_or_job","")),
                         ("Status", e.get("status",""))]:
                if v: lines.append(f"<b>{k}:</b> {v}")
            if e.get("notes"):
                n = e['notes']
                lines.append(f"<br><i>{n[:180]}{'…' if len(n) > 180 else ''}</i>")
        elif etype == "location":
            for k, v in [("Type", e.get("type","")),
                         ("Status", e.get("status","")),
                         ("Faction", e.get("faction",""))]:
                if v: lines.append(f"<b>{k}:</b> {v}")
            if e.get("notes"):
                n = e['notes']
                lines.append(f"<br>{n[:180]}{'…' if len(n) > 180 else ''}")
        elif etype == "lore":
            if e.get("category"): lines.append(f"<b>Category:</b> {e['category']}")
            if e.get("content"):
                n = e['content']
                lines.append(f"<br>{n[:180]}{'…' if len(n) > 180 else ''}")
        self._d_body.setText("<br>".join(lines) if lines else "<i>No details.</i>")

        links = e.get("linked", [])
        self._d_links_hdr.setVisible(bool(links))
        self._d_links.setText("\n".join(
            f"{TYPE_ICON.get(l.get('type',''), '•')} {l['label']}" for l in links
        ) if links else "")
        self._d_hint.hide()

    # ── annotation events ─────────────────────────────────────────────────────

    def _on_annot_deleted(self, ann_id: str):
        self.app.campaign["graph_annotations"] = [
            a for a in self.app.campaign.get("graph_annotations", [])
            if a["id"] != ann_id]
        self.app.set_dirty(True)

    # ── toolbar helpers ───────────────────────────────────────────────────────

    def _set_mode(self, mode: str):
        self._map.set_mode(mode)
        active = (f"background:{C['crimson_dim']};border:1px solid {C['crimson']};"
                  f"border-radius:4px;color:{C['parchment']};padding:4px 10px;font-size:12px;")
        idle   = (f"background:transparent;border:1px solid {C['border']};"
                  f"border-radius:4px;color:{C['text_muted']};padding:4px 10px;font-size:12px;")
        self._pan_btn.setStyleSheet(active if mode == "pan"  else idle)
        self._draw_btn.setStyleSheet(active if mode == "draw" else idle)

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._draw_color), self, "Annotation colour")
        if col.isValid():
            self._draw_color = col.name()
            self._map.set_draw_color(self._draw_color)
            self._update_swatch()

    def _update_swatch(self):
        self._color_swatch.setStyleSheet(
            f"background:{self._draw_color};border:2px solid {C['border']};border-radius:3px;")

    def _depth_changed(self, value: int):
        self._depth_val_lbl.setText(str(value))
        if self._hub_entry:
            self._rebuild_graph()

    def _rebuild_graph(self):
        """Rebuild graph with current hub, depth, saved annotations and positions."""
        if not self._hub_entry:
            return
        hub_id    = self._hub_entry["id"]
        saved     = self.app.campaign.get("graph_annotations", [])
        # Positions are keyed by hub_id so each subject has its own layout
        # Guard against old saves where graph_positions was a flat dict or list
        all_pos   = self.app.campaign.get("graph_positions", {})
        if not isinstance(all_pos, dict):
            all_pos = {}
        saved_pos = all_pos.get(hub_id, {})
        self._map.build_graph(
            self.app.campaign,
            hub_id=hub_id,
            saved_annotations=saved,
            saved_positions=saved_pos,
            max_rings=self._depth_slider.value(),
        )

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def refresh(self):
        """Called by MainWindow when navigating to this page."""
        self._picker.set_campaign(self.app.campaign)
        if self._hub_entry:
            self._rebuild_graph()
        else:
            self._picker.select_first()

    def save_graph_state(self):
        """Snapshot positions and annotations into campaign before saving."""
        self.app.campaign["graph_annotations"] = self._map.get_annotations()
        if self._hub_entry:
            hub_id = self._hub_entry["id"]
            all_pos = self.app.campaign.setdefault("graph_positions", {})
            all_pos[hub_id] = self._map.get_positions(hub_id)
        self.app.set_dirty(True)

    # keep old name as alias so nothing breaks if called from app.py
    def save_annotations(self):
        self.save_graph_state()