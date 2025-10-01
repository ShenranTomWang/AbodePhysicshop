from __future__ import annotations
from typing import List, Optional, Tuple, Union, Literal
from pydantic import BaseModel, Field

# Auxiliary
Vec3 = Tuple[float, float, float]
Color3 = Tuple[float, float, float]

# Material
class ElasticMaterial(BaseModel):
    type: Literal["Elastic"] = "Elastic"
    E: float = Field(..., description="Young's modulus")
    nu: float = Field(..., description="Poisson's ratio")
    rho: float = Field(..., description="Density")
    model: Literal["corotation", "neo_hookean", "stvk"] = "corotation"

class SnowMaterial(BaseModel):
    type: Literal["Snow"] = "Snow"
    rho: Optional[float] = None

class SandMaterial(BaseModel):
    type: Literal["Sand"] = "Sand"
    rho: Optional[float] = None

class LiquidMaterial(BaseModel):
    type: Literal["Liquid"] = "Liquid"
    rho: Optional[float] = None

Material = Union[ElasticMaterial, SnowMaterial, SandMaterial, LiquidMaterial]

# Geometry
class PlaneMorph(BaseModel):
    type: Literal["Plane"] = "Plane"

class BoxMorph(BaseModel):
    type: Literal["Box"] = "Box"
    pos: Vec3
    size: Vec3

class SphereMorph(BaseModel):
    type: Literal["Sphere"] = "Sphere"
    pos: Vec3
    radius: float

Morph = Union[PlaneMorph, BoxMorph, SphereMorph]

# Visual
class Surface(BaseModel):
    type: Literal["Default"] = "Default"
    color: Color3 = (0.9, 0.9, 0.9)
    # Genesis supports "particle" and "recon" modes in practice
    vis_mode: Optional[Literal["particle", "recon"]] = None

# Scene
class StaticObject(BaseModel):
    name: str
    morph: Morph
    surface: Surface

class MPMBody(BaseModel):
    name: str
    material: Material
    morph: Morph
    surface: Surface

# options
class SimOptions(BaseModel):
    dt: float = 1e-3
    substeps: int = 20
    gravity: Vec3 = (0.0, 0.0, -9.81)

class MPMOptions(BaseModel):
    lower_bound: Vec3 = (-1.0, -1.0, 0.0)
    upper_bound: Vec3 = (1.0, 1.0, 1.0)
    grid_density: int = 64

class VisOptions(BaseModel):
    background_color: Color3 = (0.96, 0.98, 1.0)
    visualize_mpm_boundary: bool = True

class ViewerOptions(BaseModel):
    camera_fov: float = 30.0
    camera_pos: Vec3 = (2.1, -2.1, 1.4)
    camera_lookat: Vec3 = (0.0, 0.0, 0.35)

class CaptureOptions(BaseModel):
    dir: str = "frames"
    every: int = 10

# ---------- Top-level Genesis config ----------
class GenesisConfig(BaseModel):
    show_viewer: Optional[bool] = Field(None, description="Whether to show viewer; optional in some setups")
    steps: int = 1000
    max_bodies: int = 4
    dump_particles: bool = True

    sim_options: SimOptions
    mpm_options: MPMOptions
    vis_options: Optional[VisOptions] = None
    viewer_options: Optional[ViewerOptions] = None

    static: List[StaticObject] = Field(default_factory=list)
    mpm_bodies: List[MPMBody]

    capture: Optional[CaptureOptions] = None
