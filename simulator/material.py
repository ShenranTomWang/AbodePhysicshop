from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Union, Optional
from .auxiliary import _clip
import genesis as gs

class ElasticMaterial(BaseModel):
    type: Literal["Elastic"] = "Elastic"
    E: float = 1e5
    nu: float = 0.3
    rho: float = 1000.0
    model: Literal["corotation", "neo_hookean", "stvk"] = "corotation"

    @model_validator(mode="after")
    def _ranges(self):
        self.rho = _clip(self.rho, 100.0, 10000.0)
        self.E   = _clip(self.E, 1e4, 1e10)
        self.nu  = _clip(self.nu, 0.0, 0.49)
        return self

    def to_genesis(self):
        return gs.materials.MPM.Elastic(E=self.E, nu=self.nu, rho=self.rho, model=self.model)

class SnowMaterial(BaseModel):
    type: Literal["Snow"] = "Snow"
    rho: float = 500.0

    @model_validator(mode="after")
    def _ranges(self):
        self.rho = _clip(self.rho, 50.0, 800.0)
        return self

    def to_genesis(self):
        return gs.materials.MPM.Snow(rho=self.rho)

class SandMaterial(BaseModel):
    type: Literal["Sand"] = "Sand"
    rho: float = 1600.0

    @model_validator(mode="after")
    def _ranges(self):
        self.rho = _clip(self.rho, 1200.0, 2200.0)
        return self
    
    def to_genesis(self):
        return gs.materials.MPM.Sand(rho=self.rho)

class LiquidMaterial(BaseModel):
    type: Literal["Liquid"] = "Liquid"
    rho: float = 1000.0

    @model_validator(mode="after")
    def _ranges(self):
        self.rho = _clip(self.rho, 800.0, 1300.0)
        return self

    def to_genesis(self):
        return gs.materials.MPM.Liquid(rho=self.rho)

Material = Union[ElasticMaterial, SnowMaterial, SandMaterial, LiquidMaterial]