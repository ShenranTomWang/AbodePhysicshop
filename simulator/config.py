from typing import List
from pydantic import BaseModel, Field
from .options import SimOptions, MPMOptions, VisOptions, ViewerOptions, CaptureOptions
from .scene import StaticObject, MPMBody

class GenesisConfig(BaseModel):
    show_viewer: bool
    steps: int
    max_bodies: int
    dump_particles: bool

    sim_options: SimOptions
    mpm_options: MPMOptions
    vis_options: VisOptions
    viewer_options: ViewerOptions

    static: List[StaticObject]
    mpm_bodies: List[MPMBody]

    capture: CaptureOptions
