# create_test_assets.py
from pathlib import Path
import numpy as np
import trimesh

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def build_test_suite():
    print(f"Generating pipeline test suite in {RAW_DIR}...\n")

    # 1. Perfect Solid (Fabrication PASS)
    solid_cube = trimesh.creation.box(extents=(20.0, 20.0, 20.0))
    solid_cube.export(RAW_DIR / "01_solid_cube_pass_fab.obj")
    print("[+] 01_solid_cube_pass_fab.obj: Watertight single-body solid.")

    # 2. Open Boundary Mesh (Fabrication FAIL - Not Watertight)
    open_box = trimesh.creation.box(extents=(20.0, 20.0, 20.0))
    open_box.faces = open_box.faces[:-2]  # Remove two faces to punch an open boundary
    open_box.export(RAW_DIR / "02_open_box_fail_fab.obj")
    print("[+] 02_open_box_fail_fab.obj: Missing faces, non-manifold open boundary.")

    # 3. Disjoint Multi-Body Mesh (Fabrication WARN/FAIL - 2 Shells)
    box_a = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    box_b = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    box_b.apply_translation([25.0, 0.0, 0.0])
    dual_boxes = trimesh.util.concatenate([box_a, box_b])
    dual_boxes.export(RAW_DIR / "03_dual_shell_bodies.obj")
    print("[+] 03_dual_shell_bodies.obj: Two disjoint shells in a single file.")

    # 4. Degenerate Geometry Mesh (Zero-Area Triangles)
    degen_mesh = trimesh.creation.box(extents=(15.0, 15.0, 15.0))
    # Collapse vertex 1 onto vertex 0 so adjacent faces have zero area
    degen_mesh.vertices[1] = degen_mesh.vertices[0]
    degen_mesh.export(RAW_DIR / "04_degenerate_faces.obj")
    print("[+] 04_degenerate_faces.obj: Collapsed vertices producing zero-area triangles.")

    # 5. Game Asset with UV Coordinates (Game PASS)
    uv_sphere = trimesh.creation.uv_sphere(radius=10.0)
    uv_sphere.export(RAW_DIR / "05_textured_sphere_pass_game.obj")
    print("[+] 05_textured_sphere_pass_game.obj: Contiguous topology with valid UV mapping.")

    # 6. Low-Poly Asset without UVs (Game FAIL)
    raw_cube_lines = """# OBJ without texture coordinates
v -5.0 -5.0 5.0
v 5.0 -5.0 5.0
v -5.0 5.0 5.0
v 5.0 5.0 5.0
v -5.0 5.0 -5.0
v 5.0 5.0 -5.0
v -5.0 -5.0 -5.0
v 5.0 -5.0 -5.0
f 1 2 4 3
f 3 4 6 5
f 5 6 8 7
f 7 8 2 1
f 2 8 6 4
f 7 1 3 5
"""
    (RAW_DIR / "06_no_uvs_fail_game.obj").write_text(raw_cube_lines)
    print("[+] 06_no_uvs_fail_game.obj: Valid solid geometry, but missing UV coordinates.")

    print("\nSuite generated successfully.")


if __name__ == "__main__":
    build_test_suite()