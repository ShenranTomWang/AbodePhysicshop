from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, model_validator, field_validator
from .options import SimOptions, MPMOptions, VisOptions, ViewerOptions
from .scene import StaticObject, MPMBody
from .geometry import BoxMorph
from .material import ElasticMaterial
from .visual import Surface

def _min3(a, b): return (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
def _max3(a, b): return (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))

def _aabb_union(a: Optional[Tuple[tuple, tuple]], b: Optional[Tuple[tuple, tuple]]):
    if a is None: return b
    if b is None: return a
    return _min3(a[0], b[0]), _max3(a[1], b[1])

class GenesisConfig(BaseModel):
    show_viewer: bool = True
    steps: int = 600
    max_bodies: int = 8
    dump_particles: bool = False

    sim_options: SimOptions = Field(default_factory=SimOptions)
    mpm_options: MPMOptions = Field(default_factory=MPMOptions)
    vis_options: VisOptions = Field(default_factory=VisOptions)
    viewer_options: ViewerOptions = Field(default_factory=ViewerOptions)

    static: List[StaticObject] = Field(default_factory=list)

    # Require at least one MPM body by default
    min_bodies: int = 1
    mpm_bodies: List[MPMBody] = Field(
        default_factory=lambda: [
            MPMBody(
                name="default",
                material=ElasticMaterial(),
                morph=BoxMorph(),
                surface=Surface()
            )
        ]
    )

    # --- guardrail knobs ---
    auto_fit_bounds: bool = True
    bounds_padding: float = 0.15  # fraction of scene diagonal to pad when auto-fitting
    require_bodies_inside: bool = True  # if False, we only warn (but here we repair instead)

    @model_validator(mode="after")
    def _require_bodies(self):
        if self.min_bodies > 0 and len(self.mpm_bodies) < self.min_bodies:
            raise ValueError(
                f"Expected at least {self.min_bodies} MPM body/bodies, got {len(self.mpm_bodies)}. "
                "If you really want no bodies, set min_bodies=0."
            )
        return self
    
    @field_validator("steps")
    @classmethod
    def _steps_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("steps must be >= 1")
        return v
    
    @model_validator(mode="after")
    def _check_or_fit_domain(self):
        lb, ub = self.mpm_options.lower_bound, self.mpm_options.upper_bound

        # 1) lower < upper
        if not (lb[0] < ub[0] and lb[1] < ub[1] and lb[2] < ub[2]):
            raise ValueError(f"mpm_options.lower_bound {lb} must be strictly less than upper_bound {ub} in all axes")

        # 2) scene AABB from bodies (ignore infinite planes)
        scene_aabb = None
        for body in self.mpm_bodies:
            aabb = body.morph.aabb()
            scene_aabb = _aabb_union(scene_aabb, aabb)

        # No finite bodies: nothing to check
        if scene_aabb is None:
            return self

        (bl, bu) = scene_aabb
        # 3) Are all bodies inside?
        inside = (lb[0] <= bl[0] and lb[1] <= bl[1] and lb[2] <= bl[2] and
                  ub[0] >= bu[0] and ub[1] >= bu[1] and ub[2] >= bu[2])

        if inside:
            return self

        # 4) Auto-fit if requested
        if self.auto_fit_bounds:
            # pad by a fraction of scene diagonal
            diag = ((bu[0]-bl[0])**2 + (bu[1]-bl[1])**2 + (bu[2]-bl[2])**2) ** 0.5
            pad = self.bounds_padding * max(1e-6, diag)

            new_lb = (bl[0]-pad, bl[1]-pad, bl[2]-pad)
            new_ub = (bu[0]+pad, bu[1]+pad, bu[2]+pad)
            self.mpm_options.lower_bound = new_lb
            self.mpm_options.upper_bound = new_ub
            return self

        # 5) Otherwise: fail loudly with a helpful message
        if self.require_bodies_inside:
            raise ValueError(
                "One or more bodies lie outside the simulation domain.\n"
                f"Domain: lb={lb}, ub={ub}\n"
                f"Bodies AABB: lb={bl}, ub={bu}\n"
                "Set auto_fit_bounds=True to automatically expand the domain."
            )
        return self
