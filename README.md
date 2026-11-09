# Spatial Ingestion Pipeline
<img width="1100" height="682" alt="image" src="https://github.com/user-attachments/assets/a76f64d7-e84a-4f1e-bbf0-854fcea6b7cc" />

## What it does

The Spatial Ingestion Pipeline automates geometric auditing, topological validation, and relational tracking for 3D assets (`.obj`). It intercepts raw meshes, extracts spatial properties (watertight 2-manifold closure, disjoint shell count, zero-area degenerate faces, unreferenced dead vertices, and UV coordinate presence), and applies target validation profiles (`fabrication` vs. `game`).

Valid models are committed to managed storage and registered in SQLite in an atomic transaction; meshes violating mandatory constraints trigger an immediate rollback, preventing broken geometry from entering production storage. An asynchronous PySide6 desktop dashboard provides real-time batch monitoring, search filtering, and an inspector panel with bounding envelopes and resin cost estimates.

## Running it

You need Python 3.10 or later. From the repository root:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

Install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

Initialize the relational SQLite database schema:

```bash
python -c "from src.database import init_db; init_db()"
```

Launch the desktop app:

```bash
python -m src.ui.main_window
```

Or run a headless single-asset ingestion directly:

```bash
python -c "from src.ingest import ingest_asset; res = ingest_asset('data/raw/01_solid_cube_pass_fab.obj'); print('Ingested ID:', res.asset_id, '| Watertight:', res.profile.is_watertight)"
```

Select a gatekeeper profile (`fabrication` or `game`), click **Ingest Asset...** to stage a single file, or click **Batch Directory...** to process a folder. Clicking any asset row in the table loads its bounding dimensions, net volume, shell count, and diagnostic warnings into the side inspector.

### Graph engine dependency

Counting disjoint shells via `trimesh.split()` relies on a face-adjacency graph traversal engine. `scipy` is required for compiled C graph performance on dense meshes:

```bash
python -m pip install scipy networkx
```

If neither engine is installed, topological component splitting will raise an `ImportError`.

## Trying it with generated test assets

Generate an edge-case test suite covering clean solids, open boundary boundaries, multi-body meshes, zero-area collapsed triangles, and untextured models without needing external DCC software:

```bash
python create_test_assets.py
```

This writes six targeted `.obj` files into `data/raw/`. Run a headless batch across them:

```bash
python -m src.batch fabrication
```

The terminal report breaks down passed assets staged into `data/storage/` and failed assets rolled back with detailed rejection reasons (`AssetValidationError`). Ingested records, bounding coordinates, and volume metrics persist under `data/pipeline.db`.

## How it is built

The application is written in Python. PySide6 provides the desktop interface, real-time status badges, and event handling. `trimesh` inspects raw mesh topology and half-edge closure, `scipy` analyzes connected graph components to isolate disjoint shells, and SQLite stores relational metadata with foreign-key constraints. Batch file processing runs in a dedicated `QThread` worker to keep the interface interactive during heavy geometry I/O.

- `src/extractor.py` extracts topological facts (watertightness, poly/vert count, bounding boxes, volume, degenerate face counts, UV mapping presence, unreferenced vertices).
- `src/ingest.py` handles atomic disk staging, validation profile policies (`fabrication` vs. `game`), and transaction rollbacks upon error.
- `src/database.py` manages SQLite schema definitions (`assets` and `asset_spatial_data`), data access helpers, and relational integrity.
- `src/batch.py` executes directory sweeps via `glob` pattern matching with summary error reporting.
- `src/ui/` contains the main dashboard (`main_window.py`), threaded worker (`worker.py`), and presentation widgets (`widgets.py`). 

Run a headless batch test across all assets:

```bash
python -m src.batch game
```

This is an MVP pipeline build. Ingested assets are stored canonically on disk under `data/storage/` and cataloged in `data/pipeline.db`. The current build verifies Wavefront `.obj` topology; automatic version increments (`v001`, `v002`) and I plan to add OpenUSD stage export are next. Assets flagged with warnings (such as multi-body shells) are registered in the ledger but highlighted in the inspector for artist review.
