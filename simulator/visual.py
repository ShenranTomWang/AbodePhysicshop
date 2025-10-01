from pydantic import BaseModel
from typing import Literal
from .auxiliary import Color3

class Surface(BaseModel):
    type: Literal["Default"]
    color: Color3
    vis_mode: Literal["particle", "recon"]