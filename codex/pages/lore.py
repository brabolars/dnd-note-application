"""
lore.py — LorePage panel.
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


class LorePage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent); self.app = app; self._filter="All"; self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(28,24,28,24); vl.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(lbl("LORE & WORLD NOTES", C['text_dim'], 11, True, 2)); top.addStretch()
        add = btn("+ New Entry","primary"); add.clicked.connect(self._add)
        top.addWidget(add); vl.addLayout(top)

        cats = ["All","World","Faction","Item","Place","Prophecy","History","Other"]
        pill_row = QHBoxLayout(); self._pills = {}
        for cat in cats:
            b = QPushButton(cat); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, c=cat: self._set_filter(c))
            self._pills[cat] = b; self._style_pill(b, cat=="All"); pill_row.addWidget(b)
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
                            f"color:{C['parchment']};border-radius:12px;padding:3px 12px;"
                            f"font-size:11px;font-weight:600;}}")
        else:
            b.setStyleSheet(f"QPushButton{{background:transparent;border:1px solid {C['border']};"
                            f"color:{C['text_muted']};border-radius:12px;padding:3px 12px;font-size:11px;}}"
                            f"QPushButton:hover{{border-color:{C['border_accent']};"
                            f"color:{C['text_primary']};}}")

    def _set_filter(self, cat):
        self._filter = cat
        for c,b in self._pills.items(): self._style_pill(b, c==cat)
        self.refresh()

    _CAT_COL = {
        "World":C['sky'],"Faction":C['gold'],"Item":C['green'],
        "Place":C['blue'],"Prophecy":C['crimson_glow'],"History":C['text_muted'],"Other":C['text_muted'],
    }

    def refresh(self):
        while self._cl.count() > 1:
            it = self._cl.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        entries = self.app.campaign.get("lore",[])
        if self._filter != "All":
            entries = [e for e in entries if e.get("category")==self._filter]
        if not entries:
            self._cl.insertWidget(0, EmptyState("📖","No lore entries",
                "Record world lore, factions, items, and mysteries.")); return
        for e in entries:
            card = self._make_card(e)
            self._cl.insertWidget(self._cl.count()-1, card)

    def _make_card(self, e):
        cat = e.get("category","World")
        accent = self._CAT_COL.get(cat, C['text_muted'])
        card = QFrame(); card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(
            f"QFrame{{background:{C['bg_card']};border:1px solid {C['border']};"
            f"border-left:3px solid {accent};border-radius:6px;}}"
            f"QFrame:hover{{background:{C['bg_hover']};border-color:{C['border_accent']};"
            f"border-left-color:{accent};}}")
        vl = QVBoxLayout(card); vl.setContentsMargins(12,10,12,10); vl.setSpacing(4)
        top = QHBoxLayout()
        top.addWidget(lbl(e.get("title","Untitled"), C['parchment'], 13, True))
        top.addStretch()
        top.addWidget(lbl(cat, accent, 10, True, 1))
        vl.addLayout(top)
        content = e.get("content","")
        if content:
            p = content[:150].replace("\n"," ") + ("…" if len(content)>150 else "")
            vl.addWidget(lbl(p, C['text_dim'], 11))
        if e.get("linked"):
            vl.addWidget(lbl("🔗 " + "  ·  ".join(l["label"] for l in e["linked"][:4]),
                               C['blue'], 10))
        card.mousePressEvent = lambda ev, entry=e: self._edit(entry)
        return card

    def _add(self):
        dlg = LoreDialog(campaign=self.app.campaign, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.app.campaign["lore"].append(dlg.get_data())
            self.app.set_dirty(True); self.refresh()

    def _edit(self, e):
        dlg = LoreDialog(data=e, campaign=self.app.campaign, parent=self)
        dlg.deleted.connect(self._delete)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_data()
            lst = self.app.campaign["lore"]
            for i,le in enumerate(lst):
                if le["id"]==updated["id"]: lst[i]=updated; break
            self.app.set_dirty(True); self.refresh()

    def _delete(self, eid):
        self.app.campaign["lore"] = [e for e in self.app.campaign["lore"] if e["id"]!=eid]
        self.app.set_dirty(True); self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: CONNECTIONS  —  multi-ring radial + manual annotation lines
# ══════════════════════════════════════════════════════════════════════════════

from PyQt6.QtCore import QTimer

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

# Ring geometry
RING_R   = [0, 200, 380, 540]   # px radius per ring 0-3
RING_DIM = [1.0, 0.9, 0.75, 0.6]  # opacity multiplier per ring (visual depth)
NODE_R_HUB  = 56
NODE_R_R1   = 42
NODE_R_R2   = 34
NODE_R_OUTER = 26


class AnnotationLine(QGraphicsLineItem):
    """A manually drawn visual-only connection between two nodes."""
    def __init__(self, na, nb, color, ann_id, parent=None):
        super().__init__(parent)
        self.na      = na
        self.nb      = nb
        self.ann_id  = ann_id
        self._color  = color
        pen = QPen(QColor(color), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setDashPattern([6, 4])
        self.setPen(pen)
        self.setZValue(1.5)
        self.setAcceptHoverEvents(True)
        self._update_pos()

    def _update_pos(self):
        self.setLine(self.na.x(), self.na.y(), self.nb.x(), self.nb.y())

    def sync(self):
        self._update_pos()

    def hoverEnterEvent(self, event):
        pen = self.pen(); pen.setWidth(3); self.setPen(pen)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        pen = self.pen(); pen.setWidth(2); self.setPen(pen)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)


class MindNode(QGraphicsEllipseItem):
    """Draggable node; updates all attached edges when moved."""

    def __init__(self, entry, etype, radius=NODE_R_R1, ring=1):
        self.entry  = entry
        self.etype  = etype
        self.ring   = ring
        self.is_hub = (ring == 0)
        r = radius
        super().__init__(-r, -r, r*2, r*2)
        self.radius = r
        self._dragging = False
        self._struct_edges   = []   # (QGraphicsLineItem, other_node, i_am_source)
        self._annot_edges    = []   # AnnotationLine refs to sync on move

        dim = RING_DIM[min(ring, len(RING_DIM)-1)]
        if self.is_hub:
            fill   = QColor(C['crimson_dim'])
            border = QColor(C['crimson_glow'])
            bw = 3
        else:
            fill   = QColor(TYPE_COL_DIM.get(etype, C['bg_card']))
            border = QColor(TYPE_COL.get(etype, C['border']))
            fill.setAlphaF(dim)
            border.setAlphaF(dim)
            bw = 2

        self.setBrush(fill)
        self.setPen(QPen(border, bw))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

        label = entry.get("name") or entry.get("title") or "?"
        icon  = TYPE_ICON.get(etype, "•")
        short = label[:14] + ("…" if len(label) > 14 else "")
        display = f"{icon}\n{short}"

        txt = QGraphicsTextItem(display, self)
        fsize = 8 if self.is_hub else max(6, 8 - ring)
        font = QFont("Segoe UI", fsize)
        font.setBold(self.is_hub or ring == 1)
        txt.setFont(font)
        col = QColor(C['crimson_glow'] if self.is_hub else TYPE_COL.get(etype, C['text_primary']))
        col.setAlphaF(max(0.5, dim))
        txt.setDefaultTextColor(col)
        txt.setTextWidth(r * 1.9)
        br = txt.boundingRect()
        txt.setPos(-br.width()/2, -br.height()/2)

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

    def register_struct_edge(self, line, other, is_source):
        self._struct_edges.append((line, other, is_source))

    def register_annot_edge(self, ann):
        self._annot_edges.append(ann)

    def unregister_annot_edge(self, ann):
        self._annot_edges = [a for a in self._annot_edges if a is not ann]


class MindMapView(QGraphicsView):
    node_selected    = pyqtSignal(object)   # MindNode
    annot_deleted    = pyqtSignal(str)      # ann_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet(f"background:{C['bg_deep']};border:none;")
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._nodes     = []
        self._annots    = []   # AnnotationLine items
        self._selected  = None
        self._mode      = "pan"        # "pan" | "draw"
        self._draw_first = None        # first node clicked in draw mode
        self._draw_color = C['crimson_glow']
        self._temp_line  = None        # preview line while hovering in draw mode
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    # ── public API ──

    def set_mode(self, mode):
        self._mode = mode
        self._draw_first = None
        if self._temp_line:
            self._scene.removeItem(self._temp_line)
            self._temp_line = None
        if mode == "draw":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_draw_color(self, color_hex):
        self._draw_color = color_hex

    def fit(self):
        r = self._scene.itemsBoundingRect().adjusted(-60,-60,60,60)
        self.fitInView(r, Qt.AspectRatioMode.KeepAspectRatio)

    def get_annotations(self):
        """Return serialisable list of annotation dicts."""
        return [
            {"id": a.ann_id, "from_id": a.na.entry["id"],
             "to_id": a.nb.entry["id"], "color": a._color}
            for a in self._annots
        ]

    def load_annotations(self, ann_list, node_map):
        """Restore saved annotations. node_map: id -> MindNode."""
        for ann_data in ann_list:
            fid = ann_data.get("from_id"); tid = ann_data.get("to_id")
            if fid not in node_map or tid not in node_map: continue
            na = node_map[fid]; nb = node_map[tid]
            color = ann_data.get("color", C['crimson_glow'])
            ann = AnnotationLine(na, nb, color, ann_data["id"])
            self._scene.addItem(ann)
            self._annots.append(ann)
            na.register_annot_edge(ann)
            nb.register_annot_edge(ann)

    # ── wheel / mouse ──

    def wheelEvent(self, event):
        f = 1.12 if event.angleDelta().y() > 0 else 1/1.12
        self.scale(f, f)
        event.accept()

    def mousePressEvent(self, event):
        sp   = self.mapToScene(event.pos())
        item = self._hit_node(event.pos())

        if self._mode == "draw" and event.button() == Qt.MouseButton.LeftButton:
            if item:
                if self._draw_first is None:
                    # First click — select source
                    self._draw_first = item
                    self._highlight(item, True)
                elif item is not self._draw_first:
                    # Second click — create annotation
                    self._finish_draw(item)
                else:
                    # Clicked same node twice — cancel
                    self._cancel_draw()
            else:
                self._cancel_draw()
            event.accept(); return

        if event.button() == Qt.MouseButton.RightButton:
            # Right-click on annotation line → delete it
            ann = self._hit_annot(event.pos())
            if ann:
                self._delete_annot(ann)
                event.accept(); return
            self._cancel_draw()

        if self._mode == "pan":
            if item:
                self._select(item)
                event.accept(); return
            else:
                self._select(None)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mode == "draw" and self._draw_first:
            sp = self.mapToScene(event.pos())
            if self._temp_line:
                self._scene.removeItem(self._temp_line)
            pen = QPen(QColor(self._draw_color), 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setDashPattern([6, 4])
            self._temp_line = self._scene.addLine(
                self._draw_first.x(), self._draw_first.y(), sp.x(), sp.y(), pen)
            self._temp_line.setZValue(10)
        super().mouseMoveEvent(event)

    # ── internals ──

    def _hit_node(self, vpos):
        item = self.itemAt(vpos)
        while item and not isinstance(item, MindNode):
            item = item.parentItem()
        return item if isinstance(item, MindNode) else None

    def _hit_annot(self, vpos):
        for item in self.items(vpos):
            if isinstance(item, AnnotationLine):
                return item
        return None

    def _highlight(self, node, on):
        if on:
            bright = QColor(TYPE_COL.get(node.etype, C['border']))
            bright.setAlpha(120)
            node.setBrush(bright)
        else:
            dim = RING_DIM[min(node.ring, len(RING_DIM)-1)]
            if node.is_hub:
                node.setBrush(QColor(C['crimson_dim']))
            else:
                fill = QColor(TYPE_COL_DIM.get(node.etype, C['bg_card']))
                fill.setAlphaF(dim)
                node.setBrush(fill)

    def _select(self, node):
        if self._selected:
            self._highlight(self._selected, False)
        self._selected = node
        if node:
            self._highlight(node, True)
            self.node_selected.emit(node)

    def _finish_draw(self, nb):
        na = self._draw_first
        # Cancel temp line
        if self._temp_line:
            self._scene.removeItem(self._temp_line)
            self._temp_line = None
        self._highlight(na, False)
        self._draw_first = None

        # Don't duplicate
        pair = tuple(sorted([na.entry["id"], nb.entry["id"]]))
        for existing in self._annots:
            ep = tuple(sorted([existing.na.entry["id"], existing.nb.entry["id"]]))
            if ep == pair: return

        ann_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        ann = AnnotationLine(na, nb, self._draw_color, ann_id)
        self._scene.addItem(ann)
        self._annots.append(ann)
        na.register_annot_edge(ann)
        nb.register_annot_edge(ann)

    def _cancel_draw(self):
        if self._draw_first:
            self._highlight(self._draw_first, False)
        self._draw_first = None
        if self._temp_line:
            self._scene.removeItem(self._temp_line)
            self._temp_line = None

    def _delete_annot(self, ann):
        ann.na.unregister_annot_edge(ann)
        ann.nb.unregister_annot_edge(ann)
        self._annots = [a for a in self._annots if a is not ann]
        self._scene.removeItem(ann)
        self.annot_deleted.emit(ann.ann_id)

    # ── graph build ──

    def build_graph(self, campaign, saved_annotations=None):
        import math as _m, random
        self._scene.clear()
        self._nodes.clear()
        self._annots.clear()
        self._selected = self._draw_first = None
        if self._temp_line: self._temp_line = None

        all_entries = []
        for etype, key, nk in [
            ("character", "characters", "name"),
            ("location",  "locations",  "name"),
            ("lore",      "lore",       "title"),
        ]:
            for e in campaign.get(key, []):
                all_entries.append((etype, e))

        if not all_entries:
            return {}

        link_map = {e["id"]: e for _, e in all_entries}

        # ── Ring assignment ───────────────────────────────────────────────
        # Bidirectional connection count → hub
        conn_count = {e["id"]: 0 for _, e in all_entries}
        for _, e in all_entries:
            for l in e.get("linked", []):
                lid = l.get("id")
                if lid in conn_count:
                    conn_count[e["id"]] += 1
                    conn_count[lid]     += 1

        hub_id = max(conn_count,
                     key=lambda k: (conn_count[k],
                                    link_map[k].get("name") or link_map[k].get("title", ""))
                     ) if conn_count else None

        # BFS from hub to assign rings
        ring_of = {e["id"]: 3 for _, e in all_entries}  # default outer ring
        if hub_id:
            ring_of[hub_id] = 0
            # Build adjacency from linked lists
            adj = {e["id"]: set() for _, e in all_entries}
            for _, e in all_entries:
                for l in e.get("linked", []):
                    lid = l.get("id")
                    if lid in adj:
                        adj[e["id"]].add(lid)
                        adj[lid].add(e["id"])
            frontier = [hub_id]
            for ring_num in [1, 2]:
                next_frontier = []
                for nid in frontier:
                    for nbr in adj.get(nid, []):
                        if ring_of[nbr] == 3:   # unassigned
                            ring_of[nbr] = ring_num
                            next_frontier.append(nbr)
                frontier = next_frontier

        # ── Dot grid ─────────────────────────────────────────────────────
        for gx in range(-1800, 1801, 90):
            for gy in range(-1800, 1801, 90):
                dot = self._scene.addEllipse(gx-1, gy-1, 2, 2)
                dot.setBrush(QColor(C['border']))
                dot.setPen(QPen(Qt.PenStyle.NoPen))
                dot.setZValue(0)

        # ── Draw faint ring circles ───────────────────────────────────────
        for r_px in RING_R[1:]:
            circle = self._scene.addEllipse(-r_px, -r_px, r_px*2, r_px*2)
            pen = QPen(QColor(C['border'])); pen.setStyle(Qt.PenStyle.DotLine)
            circle.setPen(pen)
            circle.setBrush(Qt.GlobalColor.transparent)
            circle.setZValue(0.5)

        # ── Place nodes on rings ──────────────────────────────────────────
        random.seed(99)
        node_map = {}
        by_ring = {0: [], 1: [], 2: [], 3: []}
        for etype, e in all_entries:
            by_ring[ring_of[e["id"]]].append((etype, e))

        NODE_R = [NODE_R_HUB, NODE_R_R1, NODE_R_R2, NODE_R_OUTER]

        for ring_num, entries_in_ring in by_ring.items():
            n = len(entries_in_ring)
            r_px = RING_R[ring_num]
            for i, (etype, e) in enumerate(entries_in_ring):
                node = MindNode(e, etype, radius=NODE_R[ring_num], ring=ring_num)
                if ring_num == 0:
                    nx, ny = 0.0, 0.0
                else:
                    # Spread evenly, with a small jitter so overlapping is rare
                    angle = 2 * _m.pi * i / max(n, 1) + random.uniform(-0.05, 0.05)
                    nx = r_px * _m.cos(angle)
                    ny = r_px * _m.sin(angle)
                node.setPos(nx, ny)
                self._scene.addItem(node)
                self._nodes.append(node)
                node_map[e["id"]] = node

        # ── Draw structural edges ─────────────────────────────────────────
        drawn_pairs = set()
        for _, e in all_entries:
            for link in e.get("linked", []):
                lid = link.get("id")
                if lid not in node_map: continue
                pair = tuple(sorted([e["id"], lid]))
                if pair in drawn_pairs: continue
                drawn_pairs.add(pair)
                na = node_map[e["id"]]
                nb = node_map[lid]
                # Edge brightness fades for outer rings
                alpha = int(255 * RING_DIM[min(max(na.ring, nb.ring), len(RING_DIM)-1)])
                col = QColor(C['border'])
                col.setAlpha(alpha)
                pen = QPen(col, 1)
                line = self._scene.addLine(na.x(), na.y(), nb.x(), nb.y(), pen)
                line.setZValue(1)
                na.register_struct_edge(line, nb, True)
                nb.register_struct_edge(line, na, False)

        # ── Restore saved annotations ─────────────────────────────────────
        if saved_annotations:
            self.load_annotations(saved_annotations, node_map)

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-200,-200,200,200))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        return node_map
