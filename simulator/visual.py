from pydantic import BaseModel
from typing import Literal, Optional
from auxiliary import Color3

class Surface(BaseModel):
    type: Literal["Default"] = "Default"
    color: Color3 = (0.9, 0.9, 0.9)
    vis_mode: Optional[Literal["particle", "recon"]] = None