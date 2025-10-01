from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from simulator.options import SimOptions, MPMOptions, VisOptions, ViewerOptions, CaptureOptions
from simulator.scene import StaticObject, MPMBody

class GenesisConfig(BaseModel):
    show_viewer: Optional[bool] = Field(None, description="Whether to show viewer; optional in some setups")
    steps: int = 1000
    max_bodies: int = 4
    dump_particles: bool = True

    sim_options: SimOptions
    mpm_options: MPMOptions
    vis_options: Optional[VisOptions] = None
    viewer_options: Optional[ViewerOptions] = None

    static: List[StaticObject] = Field(default_factory=list)
    mpm_bodies: List[MPMBody]

    capture: Optional[CaptureOptions] = None
