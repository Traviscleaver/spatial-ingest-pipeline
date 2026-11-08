from typing import Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

class AssetTableWidget(QTableWidget):

    asset_selected = Signal(int)  #takes asset_id on row seleciton

    COLUMNS = ["ID", "Asset Name", "Status", "Polys", "Watertight", "UVs", "Bodies", "Created At"]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def populate(self, assets: list[dict[str, Any]]):
        self.setRowCount(0)

        for row_index, asset in enumerate(assets):
            self.insertRow(row_index)

            # Determine overall pass/fail health
            is_watertight = bool(asset["is_watertight"])
            has_uvs = bool(asset["has_uvs"])
            body_count = asset.get("body_count", 1)
            degen_count = asset.get("degenerate_face_count", 0)

            if not is_watertight or degen_count > 0:
                status_text = "FAIL"
                status_color = QColor("#E74C3C")  # Red
            elif body_count > 1:
                status_text = "WARN"
                status_color = QColor("#F39C12")  # Orange (multi-shell)
            else:
                status_text = "PASS"
                status_color = QColor("#2ECC71")  # Green

            # Column 0: ID
            id_item = QTableWidgetItem(str(asset["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, asset["id"])
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_index, 0, id_item)

            #Asset Name
            name_item = QTableWidgetItem(asset["name"])
            font = QFont()
            font.setBold(True)
            name_item.setFont(font)
            name_item.setForeground(status_color)
            self.setItem(row_index, 1, name_item)

            #Status Badge
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(status_color)
            self.setItem(row_index, 2, status_item)

            #Polys
            poly_item = QTableWidgetItem(f"{asset['poly_count']:,}")
            poly_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row_index, 3, poly_item)

            #Watertight Status 
            wt_item = QTableWidgetItem("YES" if is_watertight else "NO")
            wt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            wt_item.setForeground(QColor("#2ECC71") if is_watertight else QColor("#E74C3C"))
            self.setItem(row_index, 4, wt_item)

            #UV Status
            uv_item = QTableWidgetItem("YES" if has_uvs else "NO")
            uv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            uv_item.setForeground(QColor("#2ECC71") if has_uvs else QColor("#95A5A6"))
            self.setItem(row_index, 5, uv_item)

            #Disjoint Body Count
            body_item = QTableWidgetItem(str(body_count))
            body_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if body_count > 1:
                body_item.setForeground(QColor("#F39C12"))
            self.setItem(row_index, 6, body_item)

            #Timestamp
            date_item = QTableWidgetItem(str(asset.get("timestamp", "")))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_index, 7, date_item)

    def _on_selection_changed(self):
        selected_rows = self.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        asset_id = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.asset_selected.emit(asset_id)


class SpatialInspectorWidget(QGroupBox):

    RESIN_COST_PER_CM3 = 0.055

    def __init__(self, parent=None):
        super().__init__("Asset Inspector", parent)
        layout = QVBoxLayout(self)

        self.name_label = QLabel("Select an asset to view profile")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 8px;")
        layout.addWidget(self.name_label)

        self.lbl_polys = QLabel("Polygons: --")
        self.lbl_verts = QLabel("Vertices: --")
        self.lbl_dims = QLabel("Dimensions (X, Y, Z): --")
        self.lbl_volume = QLabel("Net Volume: --")
        self.lbl_cost = QLabel("Est. Fabrication Cost: --")
        self.lbl_bodies = QLabel("Disjoint Shells: --")
        self.lbl_degen = QLabel("Degenerate Faces: --")
        self.lbl_uv = QLabel("UV Mapping: --")

        for lbl in (
            self.lbl_polys, self.lbl_verts, self.lbl_dims,
            self.lbl_volume, self.lbl_cost, self.lbl_bodies,
            self.lbl_degen, self.lbl_uv
        ):
            layout.addWidget(lbl)

        layout.addStretch()

    def update_profile(self, asset: dict[str, Any]):
        dx = asset["bbox_max_x"] - asset["bbox_min_x"]
        dy = asset["bbox_max_y"] - asset["bbox_min_y"]
        dz = asset["bbox_max_z"] - asset["bbox_min_z"]
        volume = asset["volume"]
        est_cost = volume * self.RESIN_COST_PER_CM3

        self.name_label.setText(f"Asset: {asset['name']} (ID: {asset['id']})")
        self.lbl_polys.setText(f"Polygons: {asset['poly_count']:,}")
        self.lbl_verts.setText(f"Vertices: {asset['vertex_count']:,}")
        self.lbl_dims.setText(f"Dimensions: {dx:.2f} × {dy:.2f} × {dz:.2f} mm")
        self.lbl_volume.setText(f"Net Volume: {volume:.3f} cm³")
        self.lbl_cost.setText(f"Est. Fabrication Cost: ${est_cost:.2f} USD")
        self.lbl_bodies.setText(f"Disjoint Shells: {asset['body_count']}")
        self.lbl_degen.setText(f"Degenerate Faces: {asset['degenerate_face_count']}")
        self.lbl_uv.setText("UV Mapping: Present" if asset["has_uvs"] else "UV Mapping: None")