from pydantic import BaseModel, field_validator
from typing import Literal, Optional
from .auxiliary import Color3

_ALLOWED = {"visual", "collision", "particle", "sdf", "recon"}

class Surface(BaseModel):
    type: Literal["Default"] = "Default"
    color: Color3 = (0.9, 0.9, 0.9)
    # vis_mode: str = "particle"
    vis_mode: Optional[str] = None

    @field_validator("vis_mode")
    @classmethod
    def normalize_vis_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        vv = v.lower()
        return vv if vv in _ALLOWED else None
    
    def to_genesis(self):
        return gs.surfaces.Default(color=self.color, vis_mode=self.vis_mode)