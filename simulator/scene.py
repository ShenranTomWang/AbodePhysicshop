from pydantic import BaseModel, field_validator, model_validator
from .geometry import Morph
from .visual import Surface
from .material import Material
from .auxiliary import _clip

class StaticObject(BaseModel):
    name: str
    morph: Morph
    surface: Surface

    @model_validator(mode="after")
    def _default_and_guard_vis(self):
        # default to visual
        if self.surface.vis_mode is None:
            self.surface.vis_mode = "visual"
        # forbid particle on static/rigid
        if self.surface.vis_mode == "particle":
            raise ValueError("Static/rigid objects cannot use vis_mode='particle'. Use 'visual', 'collision', or 'sdf'.")
        return self

class MPMBody(BaseModel):
    name: str
    material: Material
    morph: Morph
    surface: Surface 

    # @model_validator(mode="after")
    # def _default_particle_vis(self):
    #     if self.surface.vis_mode is None:
    #         self.surface.vis_mode = "particle"
    #     return self
    
    @model_validator(mode="after")
    def _default_vis_for_mpm(self):
        if self.surface.vis_mode is None:
            # Elastic MPM looks best as a surface; fluids/granular as particles
            self.surface.vis_mode = "recon" if self.material.type == "Elastic" else "particle"
        return self