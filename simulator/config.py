from typing import List
from pydantic import BaseModel, Field
from simulator.options import SimOptions, MPMOptions, VisOptions, ViewerOptions, CaptureOptions
from simulator.scene import StaticObject, MPMBody

class GenesisConfig(BaseModel):
    show_viewer: bool = Field(True, description="Whether to show viewer; optional in some setups")
    steps: int = 1000
    max_bodies: int = 4
    dump_particles: bool = True

    sim_options: SimOptions = SimOptions()
    mpm_options: MPMOptions = MPMOptions()
    vis_options: VisOptions = VisOptions()
    viewer_options: ViewerOptions = ViewerOptions()

    static: List[StaticObject] = []
    mpm_bodies: List[MPMBody] = []

    capture: CaptureOptions = CaptureOptions()
