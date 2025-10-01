from pydantic import BaseModel, Field
from typing import Literal, Optional, Tuple, Union
from auxiliary import Vec3

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