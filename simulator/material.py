from pydantic import BaseModel, Field
from typing import Literal, Union

class ElasticMaterial(BaseModel):
    type: Literal["Elastic"]
    E: float 
    nu: float
    rho: float
    model: Literal["corotation", "neo_hookean", "stvk"]

class SnowMaterial(BaseModel):
    type: Literal["Snow"]
    rho: float

class SandMaterial(BaseModel):
    type: Literal["Sand"]
    rho: float

class LiquidMaterial(BaseModel):
    type: Literal["Liquid"]
    rho: float 

Material = Union[ElasticMaterial, SnowMaterial, SandMaterial, LiquidMaterial]