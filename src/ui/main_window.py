import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.database import list_all_assets, get_asset_by_id
from src.ui.widgets import AssetTableWidget, SpatialInspectorWidget
from src.ui.worker import BatchIngestionWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spatial Ingest Pipeline - Travis Dvorak-Cleaver")
        self.resize(1100, 650)

        self.worker: BatchIngestionWorker | None = None
        self._all_assets: list[dict] = []

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Action and Navigation Bar
        action_bar = QHBoxLayout()

        self.btn_ingest_file = QPushButton("Ingest Asset...")
        self.btn_ingest_file.clicked.connect(self._on_ingest_file)
        action_bar.addWidget(self.btn_ingest_file)

        self.btn_ingest_batch = QPushButton("Batch Ingestion...")
        self.btn_ingest_batch.clicked.connect(self._on_ingest_directory)
        action_bar.addWidget(self.btn_ingest_batch)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_data)
        action_bar.addWidget(self.btn_refresh)

        self.btn_reset = QPushButton("Reset DB")
        self.btn_reset.clicked.connect(self._on_reset_db)
        action_bar.addWidget(self.btn_reset)

        action_bar.addSpacing(20)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["fabrication", "game"])
        action_bar.addWidget(self.profile_combo)

        action_bar.addSpacing(20)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter assets by name...")
        self.search_bar.textChanged.connect(self._filter_assets)
        action_bar.addWidget(self.search_bar)

        main_layout.addLayout(action_bar)

        # Content Splitter (Table Left | Inspector Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = AssetTableWidget()
        self.table.asset_selected.connect(self._on_asset_selected)
        splitter.addWidget(self.table)

        self.inspector = SpatialInspectorWidget()
        splitter.addWidget(self.inspector)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

        #Status and Progress Footer
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

    def refresh_data(self):
        self._all_assets = list_all_assets()
        self._filter_assets(self.search_bar.text())

    def _on_reset_db(self):
        conn = sqlite3.connect("data/pipeline.db")
        try:
            conn.execute("DELETE FROM asset_spatial_data")
            conn.execute("DELETE FROM assets")
            conn.execute("DELETE FROM sqlite_sequence")
            conn.commit()
        finally:
            conn.close()

        storage_dir = Path("data/storage")
        if storage_dir.exists():
            for file_path in storage_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()

        self.refresh_data()
        self.statusBar().showMessage("Database and storage reset.", 5000)

    def _filter_assets(self, query: str):
        query = query.strip().lower()
        if not query:
            self.table.populate(self._all_assets)
        else:
            filtered = [a for a in self._all_assets if query in a["name"].lower()]
            self.table.populate(filtered)

    def _on_asset_selected(self, asset_id: int):
        asset = get_asset_by_id(asset_id)
        if asset:
            self.inspector.update_profile(asset)

    def _on_ingest_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select 3D Asset", "", "Wavefront OBJ (*.obj)"
        )
        if file_path:
            self._start_ingest_batch([Path(file_path)])

    def _on_ingest_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Asset Directory")
        if dir_path:
            files = sorted(Path(dir_path).glob("*.obj"))
            if not files:
                QMessageBox.information(self, "Batch Ingestion", "No .obj files found in directory.")
                return
            self._start_ingest_batch(files)

    def _start_ingest_batch(self, files: list[Path]):
        self.btn_ingest_file.setEnabled(False)
        self.btn_ingest_batch.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(files))

        selected_profile = self.profile_combo.currentText()
        self.worker = BatchIngestionWorker(files, profile_type=selected_profile)
        self.worker.progress_updated.connect(self._on_worker_progress)
        self.worker.batch_finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_progress(self, current: int, total: int, file_name: str):
        self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"Processing ({current}/{total}): {file_name}")

    def _on_worker_finished(self, succeeded: int, failed: int):
        self.progress_bar.setVisible(False)
        self.btn_ingest_file.setEnabled(True)
        self.btn_ingest_batch.setEnabled(True)
        self.statusBar().showMessage(f"Ingestion finished: {succeeded} passed, {failed} rejected.", 5000)
        self.refresh_data()


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()

