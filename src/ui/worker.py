from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, QThread

from src.ingest import AssetValidationError, IngestionResult, ingest_asset

class BatchIngestionWorker(QThread):

    progress_updated = Signal(int, int, str) #takse current_index, total_count, file_name
    asset_succeeded = Signal(object) #takes Ingestionresult
    asset_failed = Signal(Path, str) #takes file_path, error_message
    batch_finished = Signal(int, int) #takes Succeded_count, Failed_count

    def __init__(self, file_paths: list[Path], profile_type: str = "fabrication", parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.profile_type = profile_type
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total_count = len(self.file_paths)
        succeeded_count = 0
        failed_count = 0

        for index, file_path in enumerate(self.file_paths):
            if self._is_cancelled:
                break

            self.progress_updated.emit(index + 1, total_count, str(file_path))

            try:
                result = ingest_asset(file_path, self.profile_type)
                self.asset_succeeded.emit(result)
                succeeded_count += 1
            except AssetValidationError as e:
                failed_count += 1
                reason = "; ".join(e.report.errors)
                self.asset_failed.emit(file_path, reason)
            except Exception as e:
                self.asset_failed.emit(file_path, str(e))
                failed_count += 1

        self.batch_finished.emit(succeeded_count, failed_count)