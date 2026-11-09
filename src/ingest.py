from dataclasses import dataclass
from pathlib import Path
import sqlite3
import shutil
from src.extractor import (
    SpatialProfile,
    ValidationReport,
    validate_game,
    validate_fabrication,
)

DB_PATH = Path("data/pipeline.db")
STORAGE_DIR = Path("data/storage")

class AssetValidationError(Exception):
    def __init__(self, report: ValidationReport):
        self.report = report
        super().__init__(f"Asset validation failed: {report.errors}, {report.warnings}")


@dataclass 
class IngestionResult:
    asset_id: int
    name: str
    storage_path: Path
    profile: SpatialProfile
    report: ValidationReport


def ingest_asset(
    file_path: str | Path,
    profile_type: str = "fabrication",
    db_path: str | Path = DB_PATH,   
    storage_dir: str | Path = STORAGE_DIR,
    ) -> "IngestionResult": 
            
    file_path = Path(file_path).resolve() # Resolve file path to absolute path 
        
    if not file_path.is_file():
        raise FileNotFoundError(f"Source file not found: {file_path}") # Verify file exists 


    profile = SpatialProfile.extract_file(file_path)

    if profile_type == "fabrication":
        report = validate_fabrication(profile)
    elif profile_type == "game":
        report = validate_game(profile)
    else:
        raise ValueError(f"Unknown profile type: {profile_type}")
    if not report.passed:
        raise AssetValidationError(report) # Raise an error if the validation fails
        

    storage_dir.parent.mkdir(parents=True, exist_ok=True)
    destination_path = storage_dir / file_path.name # Create acopy of the file in our storage location

    asset_name = file_path.stem # Grab the asset name from file name
    copied_file = False 

    conn = sqlite3.connect("data/pipeline.db") # Connect database and cursor
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    try:
        shutil.copy2(file_path, storage_dir) # Create a copy of the file in the storage location
        copied_file = True # Return true if the file is copied succesfully
        cursor.execute("INSERT INTO assets (name) VALUES (?)", (asset_name,)) # Upload the asset data to our new database
        existing = cursor.fetchone()
        if existing: # Check if the asset has already been ingested and raise an error if it did
            raise FileExistsError(f"Asset '{asset_name}' is already ingested (Asset ID: {existing[0]}).")
        asset_id = cursor.lastrowid
        cursor.execute( 
            """
            INSERT INTO asset_spatial_data (
                asset_id, vertex_count, poly_count, 
                bbox_min_x, bbox_min_y, bbox_min_z, 
                bbox_max_x, bbox_max_y, bbox_max_z,
                is_watertight, volume,
                degenerate_face_count, body_count,
                unreferenced_vertex_count, has_uvs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id, profile.vertex_count, profile.poly_count,
                profile.bbox_min[0], profile.bbox_min[1], profile.bbox_min[2],
                profile.bbox_max[0], profile.bbox_max[1], profile.bbox_max[2],
                int(profile.is_watertight), profile.volume,
                profile.degenerate_count, profile.body_count,
                profile.unreferenced_vertex_count, int(profile.has_uvs)
            ),
        ) 
        conn.commit()

    except Exception as e:
        conn.rollback()
        if copied_file and destination_path.exists(): # Rollback commitments incase of a fail when copying the file to storage
            destination_path.unlink()
        raise RuntimeError(f"Error ingesting asset: {e}") from e

    finally:
        conn.close()

    return IngestionResult( # Return the result with the asset id, name, storage path, and profile
        asset_id=asset_id,
        name=asset_name,
        storage_path=destination_path,
        profile=profile,
        report=report,
    )



if __name__ == "__main__":
    test_file = Path("data/raw/cube_unit.obj")
    if test_file.exists():
        res = IngestionResult.ingest_asset(test_file)
        print(f"Successfully ingested: {res.name} (ID: {res.asset_id})")