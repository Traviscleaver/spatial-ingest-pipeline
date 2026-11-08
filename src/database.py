import sqlite3
from typing import Any
from pathlib import Path
conn = sqlite3.connect("data/pipeline.db")
cursor = conn.cursor()

DB_PATH = Path("data/pipeline.db")

SCHEMA = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS assets(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

    CREATE TABLE IF NOT EXISTS asset_spatial_data (
    asset_id INTEGER PRIMARY KEY,
    vertex_count INTEGER NOT NULL,
    poly_count INTEGER NOT NULL,
    bbox_min_x REAL NOT NULL,
    bbox_min_y REAL NOT NULL,
    bbox_min_z REAL NOT NULL,
    bbox_max_x REAL NOT NULL,
    bbox_max_y REAL NOT NULL,
    bbox_max_z REAL NOT NULL,
    is_watertight INTEGER NOT NULL CHECK (is_watertight IN (0, 1)),
    volume REAL NOT NULL,
    degenerate_face_count INTEGER NOT NULL DEFAULT 0,
    body_count INTEGER NOT NULL DEFAULT 1,
    unreferenced_vertex_count INTEGER NOT NULL DEFAULT 0,
    has_uvs INTEGER NOT NULL DEFAULT 0 CHECK (has_uvs IN (0, 1)),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
    );
"""  # is_watertight is an integer with 0 and 1 as a boolean same with has_uvs.

def init_db(db_path: Path = DB_PATH) -> None:
    print("Running Database Initialization...")
    with sqlite3.connect(db_path) as conn:
        try:
            cursor.executescript(SCHEMA)

            print("Schema Created!")
        except sqlite3.Error as e:
            print(f"Error occured: {e}")
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.") # Initialize database when the module is imported

def get_asset_by_id(asset_id: int) ->  dict[str, Any] | None:
    conn = sqlite3.connect("data/pipeline.db")
    conn.row_factory = sqlite3.Row  # Enables access by the column name
    try:
        query = """
            SELECT 
                a.id, a.name, a.timestamp,
                s.vertex_count, s.poly_count, 
                s.bbox_min_x, s.bbox_min_y, 
                s.bbox_min_z, s.bbox_max_x,
                s.bbox_max_y, s.bbox_max_z,
                s.is_watertight, s.volume,
                s.degenerate_face_count, s.body_count,
                s.unreferenced_vertex_count, s.has_uvs
            FROM assets a
            LEFT JOIN asset_spatial_data s ON a.id = s.asset_id
            WHERE a.id = ?
        """
        cursor = conn.execute(query, (asset_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_all_assets(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        query = """
        SELECT 
            a.id,
            a.name,
            a.timestamp,
            s.vertex_count,
            s.poly_count,
            s.bbox_min_x,
            s.bbox_min_y,
            s.bbox_min_z,
            s.bbox_max_x,
            s.bbox_max_y,
            s.bbox_max_z,
            s.is_watertight,
            s.volume,
            s.degenerate_face_count,
            s.body_count,
            s.unreferenced_vertex_count,
            s.has_uvs
        FROM assets a
        JOIN asset_spatial_data s ON a.id = s.asset_id
        ORDER BY a.timestamp DESC;
        """
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

