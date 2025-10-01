from pydantic import BaseModel
from typing import Literal
from auxiliary import Color3

class Surface(BaseModel):
    type: Literal["Default"] = "Default"
    color: Color3 = Color3(0.7, 0.7, 0.7)
    vis_mode: Literal["particle", "recon"] = "particle"