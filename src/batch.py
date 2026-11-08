from dataclasses import dataclass, field
import sqlite3
from src.extractor import SpatialProfile
from pathlib import Path

from src.ingest import ingest_asset, IngestionResult, AssestValidationError

@dataclass
class BatchReport:
    total: int = 0
    succeeded: list[IngestionResult] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (len(self.succeeded) / self.total * 100) if self.total else 0.0 # Calculate the success rate of batch

def ingest_directory(
        directory_path: str | Path,
        profile_type: str = "fabrication",
        extension: str = "*.obj", # Set the default file extension to look for in the directory

) -> "BatchReport":
    target_dirctory = Path(directory_path).resolve()
    if not target_dirctory.is_dir():
        raise NotADirectoryError(f"Target directory not found: {target_dirctory}")

    files = sorted(target_dirctory.glob(extension)) # Single out the files in the directory 
    report = BatchReport(total=len(files))

    print (f"Starting batch ingestion for {len(files)} files in {target_dirctory} with profile type '{profile_type}' and extension '{extension}'")
    print(f"Validation Profile: {profile_type}\n" + "-" * 50)

    for file_path in files:
        try: 
            result = ingest_asset(file_path, profile_type=profile_type)
            report.succeeded.append(result)
            print(f"[Passed]: {file_path.name:<25} -> Asset ID: {result.asset_id})")
        except AssestValidationError as e:
            reason = "; ".join(e.report.errors + e.report.warnings)
            report.failed.append((file_path, reason))
            print(f"[Failed]: {file_path.name:<25} -> {reason}")
        except Exception as e:
            report.failed.append((file_path, str(e)))
            print(f"[Error]: {file_path.name:<25} -> {str(e)}")

    print("-" * 50)
    print(f"Batch ingestion completed. Total: {report.total}, Succeeded: {len(report.succeeded)}, Failed: {len(report.failed)}, Success Rate: {report.success_rate:.2f}%")
    return report


if __name__ == "__main__":
    import sys

    raw_dir = Path("data/raw")
    profile = sys.argv[1] if len(sys.argv) > 1 else "fabrication"
    ingest_directory(raw_dir, profile_type=profile, extension="*.obj")
    