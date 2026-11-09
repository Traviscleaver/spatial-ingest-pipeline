from dataclasses import dataclass, field
from pathlib import Path
import trimesh


@dataclass
class SpatialProfile:
    vertex_count: int
    poly_count: int
    bbox_min: tuple[float, float, float]  # Define the data that will be extracted 
    bbox_max: tuple[float, float, float]
    is_watertight: bool
    volume: float

    degenerate_count: int
    body_count: int
    unreferenced_vertex_count: int
    has_uvs: bool

    @classmethod
    def extract_file(cls, file_path: str | Path) -> "SpatialProfile":
        raw_mesh = trimesh.load(file_path, force="mesh", process=False) #Load raw mesh without processing to inspect UVs and degenerate triangles

        if not isinstance(raw_mesh, trimesh.Trimesh):
            raise ValueError(f"Expected single polygonal mesh, got {type(raw_mesh)}")

        raw_vertex_count = int(raw_mesh.vertices.shape[0])
        poly_count = int(raw_mesh.faces.shape[0])

        has_uvs = bool(
            hasattr(raw_mesh.visual, "uv")
            and raw_mesh.visual.uv is not None
            and len(raw_mesh.visual.uv) > 0
        )

        referenced_vertices = set(raw_mesh.faces.flatten())
        unreferenced_vertex_count = max(0, raw_vertex_count - len(referenced_vertices))

        degenerate_count = int((raw_mesh.area_faces < 1e-6).sum())


        geo_mesh = trimesh.Trimesh( #Construct a pure geometric mesh (no TextureVisuals) so UV seams
            vertices=raw_mesh.vertices.copy(), # never break watertightness or crash mesh.split()
            faces=raw_mesh.faces.copy(),
            process=True,
        )

        is_watertight = bool(geo_mesh.is_watertight) and degenerate_count == 0
        volume = float(geo_mesh.volume) if is_watertight else 0.0

        bodies = geo_mesh.split(only_watertight=False)
        body_count = len(bodies) if hasattr(bodies, "__len__") else 1

        return cls(
            vertex_count=int(geo_mesh.vertices.shape[0]),
            poly_count=poly_count,
            bbox_min=tuple(float(v) for v in geo_mesh.bounds[0]),
            bbox_max=tuple(float(v) for v in geo_mesh.bounds[1]),
            is_watertight=is_watertight,
            volume=volume,
            degenerate_count=degenerate_count,
            body_count=body_count,
            unreferenced_vertex_count=unreferenced_vertex_count,
            has_uvs=has_uvs,
        )


@dataclass
class ValidationReport:
    passed: bool
    rule_set: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, float | int | bool] = field(default_factory=dict)


def validate_fabrication(
    profile: SpatialProfile,
    max_build_box: tuple[float, float, float] = (150.0, 150.0, 150.0),
) -> ValidationReport:
    errors = []
    warnings = []

    if not profile.is_watertight:
        errors.append("Mesh is not watertight; will cause issues in fabrication.")

    if profile.volume <= 0.0: # Perform a series of checks on the mesh and return a validation report with errors and warnings to see if it passses
        errors.append(f"Invalid volume: {profile.volume: .2f} cm3")

    if profile.degenerate_count > 0:
        errors.append(
            f"Mesh has {profile.degenerate_count} degenerate faces and may cause issues in fabrication."
        )

    if profile.body_count > 1:
        warnings.append(
            f"Mesh has {profile.body_count} separate bodies and may cause issues in fabrication."
        )

    dx = profile.bbox_max[0] - profile.bbox_min[0]
    dy = profile.bbox_max[1] - profile.bbox_min[1]
    dz = profile.bbox_max[2] - profile.bbox_min[2]

    if dx > max_build_box[0] or dy > max_build_box[1] or dz > max_build_box[2]:
        errors.append(
            f"Mesh exceeds the maximum build box dimensions: {dx:.2f} x {dy:.2f} x {dz:.2f} cm"  # Check box dimensions against max build size for fabricator
        )

    return ValidationReport(
        passed=len(errors) == 0,
        rule_set="Fabrication_RP",
        errors=errors,
        warnings=warnings,
        metrics={
            "is_watertight": profile.is_watertight,
            "volume": profile.volume,
            "dim_x": dx,
            "dim_y": dy,
            "dim_z": dz,
        },
    )


def validate_game(  #Validate game ingestion
    profile: SpatialProfile, max_triangles: int = 20000
) -> ValidationReport:
    errors = []
    warnings = []

    if profile.poly_count > max_triangles:
        errors.append(
            f"Mesh exceeds the maximum triangle count: {profile.poly_count} > {max_triangles}" #Check if too many poly counts which would cause lag. 
        )

    if not profile.is_watertight:
        warnings.append("Mesh is not watertight; may cause issues.")

    if not profile.has_uvs:
        errors.append("Mesh does not have UVs and will cause issues.")

    if profile.degenerate_count > 0:
        errors.append(
            f"Mesh has {profile.degenerate_count} degenerate zero-area faces."
        )

    if profile.unreferenced_vertex_count > 0:
        warnings.append(
            f"Mesh has {profile.unreferenced_vertex_count} unreferenced vertices and may cause issues."
        )

    if abs(profile.bbox_min[2]) > 0.05:
        warnings.append(
            f"Pivot offset Base min Z is at {profile.bbox_min[2]:.2f} cm. Not resting on Z=0."
        )

    return ValidationReport( #Return report and if it passed
        passed=len(errors) == 0,
        rule_set="Game_Ready",
        errors=errors,
        warnings=warnings,
        metrics={
            "poly_count": profile.poly_count,
            "vertex_count": profile.vertex_count,
        },
    )


if __name__ == "__main__":
    test_path = Path("data/raw/test2.obj")
    if test_path.exists():
        profile = SpatialProfile.extract_file(test_path)
        print(f"Extracted profile for {test_path.name}:")
        print(f"  - Watertight: {profile.is_watertight}")
        print(f"  - Bodies: {profile.body_count}")
        print(f"  - Degenerate faces: {profile.degenerate_count}")