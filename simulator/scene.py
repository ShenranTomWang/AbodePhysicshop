from pydantic import BaseModel
from .geometry import Morph
from .visual import Surface
from .material import Material

class StaticObject(BaseModel):
    name: str
    morph: Morph
    surface: Surface = Surface()

class MPMBody(BaseModel):
    name: str
    material: Material
    morph: Morph
    surface: Surface = Surface()