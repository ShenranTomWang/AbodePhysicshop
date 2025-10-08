from pydantic import BaseModel
from typing import Literal, Union, Tuple
from .auxiliary import Vec3

def _v3(x: Vec3) -> Tuple[float, float, float]:
    return (float(x[0]), float(x[1]), float(x[2]))

class PlaneMorph(BaseModel):
    type: Literal["Plane"] = "Plane"
    def aabb(self):
        return None

class BoxMorph(BaseModel):
    type: Literal["Box"] = "Box"
    pos: Vec3
    size: Vec3

    def aabb(self):
        px, py, pz = _v3(self.pos)
        sx, sy, sz = _v3(self.size)
        # interpret size as full lengths; half-extent on each side
        hx, hy, hz = 0.5*abs(sx), 0.5*abs(sy), 0.5*abs(sz)
        lb = (px - hx, py - hy, pz - hz)
        ub = (px + hx, py + hy, pz + hz)
        return lb, ub

class SphereMorph(BaseModel):
    type: Literal["Sphere"] = "Sphere"
    pos: Vec3
    radius: float

    def aabb(self):
        px, py, pz = _v3(self.pos)
        r = float(abs(self.radius))
        lb = (px - r, py - r, pz - r)
        ub = (px + r, py + r, pz + r)
        return lb, ub

Morph = Union[PlaneMorph, BoxMorph, SphereMorph]