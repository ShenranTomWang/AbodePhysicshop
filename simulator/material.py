from pydantic import BaseModel, Field
from typing import Literal, Optional, Union

class ElasticMaterial(BaseModel):
    type: Literal["Elastic"] = "Elastic"
    E: float = Field(..., description="Young's modulus")
    nu: float = Field(..., description="Poisson's ratio")
    rho: float = Field(..., description="Density")
    model: Literal["corotation", "neo_hookean", "stvk"] = "corotation"

class SnowMaterial(BaseModel):
    type: Literal["Snow"] = "Snow"
    rho: Optional[float] = None

class SandMaterial(BaseModel):
    type: Literal["Sand"] = "Sand"
    rho: Optional[float] = None

class LiquidMaterial(BaseModel):
    type: Literal["Liquid"] = "Liquid"
    rho: Optional[float] = None

Material = Union[ElasticMaterial, SnowMaterial, SandMaterial, LiquidMaterial]