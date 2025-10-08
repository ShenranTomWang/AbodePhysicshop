from pydantic import BaseModel, field_validator, model_validator
from .auxiliary import Vec3, Color3, _clip
import math
class SimOptions(BaseModel):
    dt: float = 1e-3
    substeps: int = 10
    gravity: Vec3 = (0.0, 0.0, -9.81)

    @model_validator(mode="after")
    def _ranges(self):
        self.dt = _clip(self.dt, 1e-5, 5e-3)
        self.substeps = int(_clip(int(self.substeps), 1, 50))
        # limit |g| to <= 50 m/s^2
        if self.gravity and len(self.gravity) == 3:
            gx, gy, gz = self.gravity
            mag = math.sqrt(gx*gx + gy*gy + gz*gz)
            if mag > 50:
                s = 50.0 / mag
                self.gravity = (gx*s, gy*s, gz*s)
        return self

    @field_validator("dt")
    @classmethod
    def check_dt(cls, v: float) -> float:
        if v <= 0 or v > 0.1:
            raise ValueError("dt should be in (0, 0.1].")
        return v
    
    @field_validator("substeps")
    @classmethod
    def check_substeps(cls, v: int) -> int:
        if v < 1 or v > 10000:
            raise ValueError("substeps must be >= 1 (and reasonably bounded).")
        return v

class MPMOptions(BaseModel):
    lower_bound: Vec3 = (-1.0, -1.0, 0.0)
    upper_bound: Vec3 = (1.0, 1.0, 1.5)
    grid_density: int = 16

    @model_validator(mode="after")
    def _ranges(self):
        self.grid_density = int(_clip(int(self.grid_density), 16, 512))
        # (optional) ensure bounds are ordered
        lb, ub = list(self.lower_bound), list(self.upper_bound)
        for i in range(3):
            if lb[i] > ub[i]:
                lb[i], ub[i] = ub[i], lb[i]
        self.lower_bound, self.upper_bound = tuple(lb), tuple(ub)
        return self

    @field_validator("grid_density")
    @classmethod
    def check_res(cls, v: int) -> int:
        if v < 8:
            raise ValueError("grid_density too small (<8).")
        return v

class VisOptions(BaseModel):
    background_color: Color3 = (1.0, 1.0, 1.0)
    visualize_mpm_boundary: bool = True

class ViewerOptions(BaseModel):
    camera_fov: float = 35.0
    camera_pos: Vec3 = (2.0, -2.0, 1.5)
    camera_lookat: Vec3 = (0.0, 0.0, 0.5)

class CaptureOptions(BaseModel):
    dir: str = "frames"
    every: int = 20