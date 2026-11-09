# create_test_assets.py
from pathlib import Path

import numpy as np
import trimesh


# Asset                              Fabrication                          Game

# 01 solid cube                      Pass                                 Fail: missing UVs
# 02 open box                        Fail: not watertight, zero volume    Fail: missing UVs; warns about open mesh and pivot
# 03 dual shells                     Pass with separate-bodies warning    Pass with pivot warning
# 04 degenerate mesh                 Fail: degenerate, not watertight     Fail: degenerate and missing UVs; warns about open mesh and pivot
# 05 grounded textured sphere        Pass                                 Pass
# 06 high-poly sphere without UVs    Pass                                 Fail: exceeds 20,000 triangles and lacks UVs

RAW_DIR = Path("data/raw")


def _write_obj(
    mesh: trimesh.Trimesh,
    file_path: Path,
    uv_coords: np.ndarray | None = None,
) -> None:
    lines = ["# Generated spatial-ingest test asset"]
    lines.extend(
        f"v {x:.9g} {y:.9g} {z:.9g}" for x, y, z in mesh.vertices
    )

    if uv_coords is not None:
        if len(uv_coords) != len(mesh.vertices):
            raise ValueError("UV coordinate count must match vertex count.")
        lines.extend(f"vt {u:.9g} {v:.9g}" for u, v in uv_coords)

    for face in mesh.faces:
        indices = face + 1
        if uv_coords is None:
            lines.append("f " + " ".join(str(index) for index in indices))
        else:
            lines.append(
                "f " + " ".join(f"{index}/{index}" for index in indices)
            )

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _spherical_uv(mesh: trimesh.Trimesh, radius: float) -> np.ndarray:
    vertices = mesh.vertices
    u = 0.5 + np.arctan2(vertices[:, 0], vertices[:, 2]) / (2 * np.pi)
    v = 0.5 - np.arcsin(
        np.clip(vertices[:, 1] / radius, -1.0, 1.0)
    ) / np.pi
    return np.column_stack((u, v))


def _planar_uv(mesh: trimesh.Trimesh) -> np.ndarray:
    xy = mesh.vertices[:, :2]
    minimum = xy.min(axis=0)
    extent = np.ptp(xy, axis=0)
    extent[extent == 0] = 1.0
    return (xy - minimum) / extent


def build_test_suite(output_dir: str | Path = RAW_DIR) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating pipeline test suite in {output_dir}...\n")

    # 01: Solid Cube (Watertight, grounded at Z=0, no UVs)
    solid_cube = trimesh.creation.box(extents=(20.0, 20.0, 20.0))
    solid_cube.apply_translation([0.0, 0.0, 10.0])
    _write_obj(solid_cube, output_dir / "01_solid_cube_pass_fab.obj")
    print("[+] 01_solid_cube_pass_fab.obj: Fabrication pass; Game fail (missing UVs).")

    # 02: Open Box (Missing 2 faces, centered at origin so min Z = -10.0, no UVs)
    open_box = trimesh.creation.box(extents=(20.0, 20.0, 20.0))
    open_box.faces = open_box.faces[:-2]
    _write_obj(open_box, output_dir / "02_open_box_fail_fab.obj")
    print("[+] 02_open_box_fail_fab.obj: Fabrication fail (not watertight, zero volume); Game fail (missing UVs, warns open mesh & pivot).")

    # 03: Dual Shells (2 watertight bodies, UV-mapped, min Z = 2.0 for pivot warning)
    box_a = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    box_b = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    box_b.apply_translation([25.0, 0.0, 0.0])
    dual_boxes = trimesh.util.concatenate([box_a, box_b])
    dual_boxes.apply_translation([0.0, 0.0, 7.0])
    _write_obj(
        dual_boxes,
        output_dir / "03_dual_shell_bodies.obj",
        _planar_uv(dual_boxes),
    )
    print("[+] 03_dual_shell_bodies.obj: Fabrication pass (separate-bodies warning); Game pass (pivot warning).")

    # 04: Degenerate Mesh (Collapsed edge producing zero-area faces & non-watertight seam, min Z = -7.5, no UVs)
    degenerate_mesh = trimesh.creation.box(extents=(15.0, 15.0, 15.0))
    degenerate_mesh.vertices[1] = degenerate_mesh.vertices[0]
    _write_obj(degenerate_mesh, output_dir / "04_degenerate_faces.obj")
    print("[+] 04_degenerate_faces.obj: Fabrication fail (degenerate, not watertight); Game fail (degenerate & missing UVs, warns open mesh & pivot).")

    # 05: Grounded Textured Sphere (3,840 tris, UV-mapped prior to Z translation, grounded at Z=0)
    sphere_radius = 10.0
    sphere = trimesh.creation.uv_sphere(radius=sphere_radius)
    sphere_uvs = _spherical_uv(sphere, sphere_radius)
    sphere.apply_translation([0.0, 0.0, sphere_radius])
    _write_obj(
        sphere,
        output_dir / "05_textured_sphere_pass_game.obj",
        sphere_uvs,
    )
    print("[+] 05_textured_sphere_pass_game.obj: Fabrication pass; Game pass (grounded and UV-mapped).")

    # 06: High-Poly Sphere Without UVs (20,480 tris > 20,000 limit, watertight, grounded at Z=0, no UVs)
    high_poly_sphere = trimesh.creation.icosphere(subdivisions=5, radius=10.0)
    high_poly_sphere.apply_translation([0.0, 0.0, 10.0])
    _write_obj(high_poly_sphere, output_dir / "06_no_uvs_fail_game.obj")
    print("[+] 06_no_uvs_fail_game.obj: Fabrication pass; Game fail (exceeds 20,000 triangles and lacks UVs).")

    print("\nSuite generated successfully.")


if __name__ == "__main__":
    build_test_suite()