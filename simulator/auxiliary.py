from typing import Tuple

Vec3 = Tuple[float, float, float]
Color3 = Tuple[float, float, float]

def _clip(x, lo, hi): 
    return max(lo, min(hi, x))