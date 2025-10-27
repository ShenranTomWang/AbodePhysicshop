from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, model_validator, field_validator
from .options import SimOptions, MPMOptions, VisOptions, ViewerOptions
from .scene import StaticObject, MPMBody
from .geometry import BoxMorph
from .material import ElasticMaterial
from .visual import Surface
import math

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
        
        lb = tuple(self.mpm_options.lower_bound)
        ub = tuple(self.mpm_options.upper_bound)

        # 1) lower < upper
        if not (lb[0] < ub[0] and lb[1] < ub[1] and lb[2] < ub[2]):
            raise ValueError(
                f"mpm_options.lower_bound {lb} must be strictly less than upper_bound {ub}"
            )

        # 2) Build bodies' axis-aligned bounding box (AABB) from morphs
        bodies_aabb = None  # Optional[Tuple[Vec3, Vec3]]
        for body in self.mpm_bodies:
            aabb = body.morph.aabb()  # Plane returns None; Box/Sphere return (lb, ub)
            if aabb is None:
                continue
            bodies_aabb = _aabb_union(bodies_aabb, aabb)

        # If no finite AABB (e.g., no MPM bodies), nothing to check
        if bodies_aabb is None:
            return self

        bl, bu = bodies_aabb  # <-- bodies' lower/upper corners

        # 3) Estimate Genesis "safety padding" (effective box is smaller than raw)
        #    Heuristic: ~2 grid cells along the largest dimension is robust.
        ext = (ub[0] - lb[0], ub[1] - lb[1], ub[2] - lb[2])
        largest_extent = max(ext)
        gd = max(1, int(getattr(self.mpm_options, "grid_density", 128)))
        cell = largest_extent / float(gd)
        safety = 2.0 * cell

        eff_lb = (lb[0] + safety, lb[1] + safety, lb[2] + safety)
        eff_ub = (ub[0] - safety, ub[1] - safety, ub[2] - safety)

        # 4) Do bodies fit inside the *effective* solver box?
        inside_effective = (
            bl[0] >= eff_lb[0] and bl[1] >= eff_lb[1] and bl[2] >= eff_lb[2] and
            bu[0] <= eff_ub[0] and bu[1] <= eff_ub[1] and bu[2] <= eff_ub[2]
        )
        if inside_effective:
            return self

        # 5) If not, either auto-expand or fail with a helpful error
        if self.auto_fit_bounds:
            # Use the larger of: user pad (as fraction of scene diagonal) vs safety
            diag = math.dist(bl, bu)
            pad = max(float(self.bounds_padding) * diag, safety)

            new_lb = (min(lb[0], bl[0] - pad), min(lb[1], bl[1] - pad), min(lb[2], bl[2] - pad))
            new_ub = (max(ub[0], bu[0] + pad), max(ub[1], bu[1] + pad), max(ub[2], bu[2] + pad))

            self.mpm_options.lower_bound = new_lb
            self.mpm_options.upper_bound = new_ub
            return self

        if self.require_bodies_inside:
            raise ValueError(
                "One or more bodies lie outside the *effective* simulation domain "
                "(Genesis shrinks the raw domain by a safety padding).\n"
                f"Raw domain:    lb={lb}, ub={ub}\n"
                f"Effective box: lb={eff_lb}, ub={eff_ub}  (safety≈{safety:.4f})\n"
                f"Bodies AABB:   lb={bl},  ub={bu}\n"
                "Enable auto_fit_bounds=True or enlarge mpm_options bounds."
            )

        return self
