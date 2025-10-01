from pydantic import BaseModel
from .auxiliary import Vec3, Color3

class SimOptions(BaseModel):
    dt: float
    substeps: int
    gravity: Vec3

class MPMOptions(BaseModel):
    lower_bound: Vec3
    upper_bound: Vec3
    grid_density: int

class VisOptions(BaseModel):
    background_color: Color3
    visualize_mpm_boundary: bool

class ViewerOptions(BaseModel):
    camera_fov: float 
    camera_pos: Vec3
    camera_lookat: Vec3

class CaptureOptions(BaseModel):
    dir: str
    every: int