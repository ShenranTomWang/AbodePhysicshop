from pydantic import BaseModel
from auxiliary import Vec3, Color3

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