#!/usr/bin/env python3
"""
Minimal Genesis MPM runner that reads all parameters from a JSON file.

Usage:
  python mpm_from_json.py --config config.json

Requires:
  pip install genesis-world torch
"""

import json, argparse, os, sys, time
import genesis as gs

from typing import Dict, Tuple, Optional, Any

Vec3 = Tuple[float, float, float]

def _v3(v) -> Vec3:
    return (float(v[0]), float(v[1]), float(v[2]))

def _min3(a: Vec3, b: Vec3) -> Vec3:
    return (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))

def _max3(a: Vec3, b: Vec3) -> Vec3:
    return (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))

def _aabb_union(a: Optional[Tuple[Vec3, Vec3]], b: Optional[Tuple[Vec3, Vec3]]):
    if a is None: return b
    if b is None: return a
    return _min3(a[0], b[0]), _max3(a[1], b[1])

def morph_aabb(morph: Dict[str, Any]) -> Optional[Tuple[Vec3, Vec3]]:
    """Finite AABB for known morphs; None for infinite (Plane) or unknown."""
    if not morph:
        return None
    t = (morph.get("type") or "").lower()
    if t == "sphere":
        px, py, pz = _v3(morph.get("pos", (0, 0, 0)))
        r = float(abs(morph.get("radius", 0.0)))
        return (px - r, py - r, pz - r), (px + r, py + r, pz + r)
    if t == "box":
        px, py, pz = _v3(morph.get("pos", (0, 0, 0)))
        sx, sy, sz = _v3(morph.get("size", (0, 0, 0)))
        hx, hy, hz = 0.5 * abs(sx), 0.5 * abs(sy), 0.5 * abs(sz)
        return (px - hx, py - hy, pz - hz), (px + hx, py + hy, pz + hz)
    if t == "plane":
        return None
    return None

_VIS_ALLOWED = {"visual", "collision", "particle", "sdf", "recon"}
# _VIS_ALIAS = {"visual": "particle", "collision": "particle", "sdf": "recon"}

def normalize_vis_mode(v: Optional[str], default: str) -> str:
    if not v:
        return default
    vv = v.lower()
    # vv = _VIS_ALIAS.get(vv, vv)
    return vv if vv in _VIS_ALLOWED else default

def sanitize_config(cfg: Dict[str, Any], *, auto_fit: bool = True, pad_frac: float = 0.15) -> Dict[str, Any]:
    """
    Make a raw JSON config safe for Genesis:
    - fill defaults, fix steps, normalize capture/vis_mode
    - check bounds and optionally auto-fit around bodies' AABB
    """
    c = dict(cfg)  # shallow copy

    # Basics
    c["show_viewer"] = bool(c.get("show_viewer", True))
    c["steps"] = max(1, int(c.get("steps", 600)))
    c["max_bodies"] = int(c.get("max_bodies", 8))
    c["dump_particles"] = bool(c.get("dump_particles", False))

    # Options blocks with safe defaults
    sim = c.get("sim_options") or {}
    sim.setdefault("dt", 1e-3)
    sim["dt"] = float(sim["dt"])
    if not (0.0 < sim["dt"] <= 0.1):
        sim["dt"] = 1e-3
    sim["substeps"] = max(1, int(sim.get("substeps", 10)))
    sim.setdefault("gravity", [0.0, 0.0, -9.81])
    c["sim_options"] = sim

    mpm = c.get("mpm_options") or {}
    mpm.setdefault("lower_bound", [-1.0, -1.0, 0.0])
    mpm.setdefault("upper_bound", [ 1.0,  1.0, 1.5])
    mpm["grid_density"] = max(8, int(mpm.get("grid_density", 64)))
    lb, ub = _v3(mpm["lower_bound"]), _v3(mpm["upper_bound"])
    if not (lb[0] < ub[0] and lb[1] < ub[1] and lb[2] < ub[2]):
        raise ValueError(f"mpm_options bounds invalid: lower_bound={lb}, upper_bound={ub}")
    c["mpm_options"] = {**mpm, "lower_bound": lb, "upper_bound": ub}

    vis = c.get("vis_options") or {}
    vis.setdefault("background_color", [1.0, 1.0, 1.0])
    vis.setdefault("visualize_mpm_boundary", True)
    c["vis_options"] = vis

    viewer = c.get("viewer_options") or {}
    viewer.setdefault("camera_fov", 35.0)
    viewer.setdefault("camera_pos", [2.0, -2.0, 1.5])
    viewer.setdefault("camera_lookat", [0.0, 0.0, 0.5])
    c["viewer_options"] = viewer

    # Scene lists, normalize surfaces
    statics = list(c.get("static") or [])
    bodies  = list(c.get("mpm_bodies") or [])
    # for obj in statics + bodies:
    #     surf = obj.get("surface") or {}
    #     # surf["vis_mode"] = normalize_vis_mode(surf.get("vis_mode"))
    #     surf["vis_mode"] = surf.get("vis_mode")
    #     obj["surface"] = surf
    # c["static"] = statics
    # c["mpm_bodies"] = bodies
    # Statics: default to 'visual' (mesh-style rendering), keep explicit choices
    for obj in statics:
        surf = obj.get("surface") or {}
        surf["vis_mode"] = normalize_vis_mode(surf.get("vis_mode"), default="visual")
        obj["surface"] = surf

    # MPM bodies: default based on material type
    for obj in bodies:
        surf = obj.get("surface") or {}
        mat_type = ((obj.get("material") or {}).get("type") or "").lower()
        default_mode = "recon" if mat_type == "elastic" else "particle"
        surf["vis_mode"] = normalize_vis_mode(surf.get("vis_mode"), default=default_mode)
        obj["surface"] = surf

    c["static"] = statics
    c["mpm_bodies"] = bodies

    # capture: avoid None so code can safely .get(...)
    cap = c.get("capture")
    c["capture"] = cap if isinstance(cap, dict) else {}

    # Auto-fit domain to finite bodies if needed
    bodies_aabb = None
    for b in bodies:
        bodies_aabb = _aabb_union(bodies_aabb, morph_aabb(b.get("morph")))
    if bodies_aabb is not None:
        bl, bu = bodies_aabb
        inside = (lb[0] <= bl[0] and lb[1] <= bl[1] and lb[2] <= bl[2] and
                  ub[0] >= bu[0] and ub[1] >= bu[1] and ub[2] >= bu[2])
        if not inside:
            if auto_fit:
                diag = ((bu[0]-bl[0])**2 + (bu[1]-bl[1])**2 + (bu[2]-bl[2])**2) ** 0.5
                pad  = max(1e-6, float(pad_frac) * diag)
                c["mpm_options"]["lower_bound"] = (bl[0]-pad, bl[1]-pad, bl[2]-pad)
                c["mpm_options"]["upper_bound"] = (bu[0]+pad, bu[1]+pad, bu[2]+pad)
            else:
                raise ValueError(
                    "Bodies lie outside the simulation domain.\n"
                    f"Domain lb/ub: {lb} / {ub}\n"
                    f"Bodies AABB:  {bl} / {bu}\n"
                    "Enable auto_fit or enlarge bounds in mpm_options."
                )
    return c

# ---------- Material & Morph factories ----------

def make_mpm_material(spec: dict):
    """Create a Genesis MPM material from a JSON spec."""
    kind = spec.get("type", "Elastic").lower()
    params = {k: v for k, v in spec.items() if k != "type"}

    if kind == "elastic":
        return gs.materials.MPM.Elastic(**params)
    elif kind in ("elastoplastic", "elasto_plastic", "plastic"):
        return gs.materials.MPM.ElastoPlastic(**params)
    elif kind == "sand":
        return gs.materials.MPM.Sand(**params)
    elif kind == "snow":
        return gs.materials.MPM.Snow(**params)
    elif kind == "liquid":
        return gs.materials.MPM.Liquid(**params)
    else:
        raise ValueError(f"Unknown MPM material type: {spec.get('type')}")

def make_morph(spec: dict):
    """Create a shape/morph from a JSON spec."""
    kind = spec.get("type", "Box").lower()
    params = {k: v for k, v in spec.items() if k != "type"}

    if kind == "box":
        return gs.morphs.Box(**params)
    elif kind == "sphere":
        return gs.morphs.Sphere(**params)
    elif kind == "plane":
        return gs.morphs.Plane(**params)
    elif kind == "mesh":
        # expects: path=..., scale=..., pos=..., rot=...
        return gs.morphs.Mesh(**params)
    else:
        raise ValueError(f"Unknown morph type: {spec.get('type')}")

def make_surface(spec: dict | None):
    if not spec:
        return gs.surfaces.Default()
    kind = spec.get("type", "Default")
    params = {k: v for k, v in spec.items() if k != "type"}
    if hasattr(gs.surfaces, kind):
        return getattr(gs.surfaces, kind)(**params)
    return gs.surfaces.Default(**params)

# ---------- Scene builder from JSON ----------

def build_scene(cfg: dict):
    gs.init()

    sim_opt    = cfg.get("sim_options")   or {}
    mpm_opt    = cfg.get("mpm_options")   or {}
    vis_opt    = cfg.get("vis_options")   or {}
    viewer_opt = cfg.get("viewer_options")or {}
    show_viewer = bool(cfg.get("show_viewer", True))

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(**sim_opt),
        mpm_options=gs.options.MPMOptions(**mpm_opt),
        vis_options=gs.options.VisOptions(**vis_opt),
        viewer_options=gs.options.ViewerOptions(**viewer_opt),
        show_viewer=show_viewer
    )

    # Static geometry (e.g., planes, meshes) under "static"
    for ent in (cfg.get("static") or []):
        morph = make_morph(ent["morph"])
        surface = make_surface(ent.get("surface"))
        scene.add_entity(morph=morph, surface=surface)

    # MPM bodies under "mpm_bodies"
    mpm_entities = []
    for ent in (cfg.get("mpm_bodies") or []):
        material = make_mpm_material(ent["material"])
        morph = make_morph(ent["morph"])
        surface = make_surface(ent.get("surface"))
        m = scene.add_entity(material=material, morph=morph, surface=surface)
        mpm_entities.append(m)

    scene.build()
    return scene, mpm_entities


# =============================================================================
# Simulation loop
# =============================================================================

def run(cfg: dict):
    scene, bodies = build_scene(cfg)

    nsteps = max(1, int(cfg.get("steps", 600)))
    capture = cfg.get("capture") or {}
    capture_dir = capture.get("dir")
    capture_rate = int(capture.get("every", 10))
    dump_particles = bool(cfg.get("dump_particles", False))

    if capture_dir:
        os.makedirs(capture_dir, exist_ok=True)
        print(f"[info] Capturing frames to: {capture_dir}")

    t0 = time.time()
    for step in range(nsteps):
        scene.step()
        if capture_dir and (step % capture_rate == 0):
            img_path = os.path.join(capture_dir, f"frame_{step:05d}.png")
            try:
                scene.viewer.screenshot(img_path)  # available when show_viewer=True
            except Exception:
                # headless fallback (if viewer not present)
                pass

    dt = time.time() - t0
    print(f"[done] Simulated {nsteps} steps in {dt:.2f}s")

    if dump_particles and bodies:
        for i, b in enumerate(bodies):
            try:
                pts = b.get_particles()
                print(f"body[{i}] particles: {len(pts)}")
            except Exception:
                print(f"body[{i}] particle dump not available on this backend")


# =============================================================================
# CLI
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description="Run a Genesis MPM sim from JSON config.")
    ap.add_argument("--config", "-c", required=True, help="Path to JSON config file.")
    ap.add_argument("--strict", action="store_true",
                    help="Fail if bodies are out of domain instead of auto-fitting bounds.")
    args = ap.parse_args()

    with open(args.config, "r") as f:
        raw = json.load(f)

    # Repair/validate BEFORE touching Genesis
    cfg = sanitize_config(raw, auto_fit=not args.strict, pad_frac=0.15)

    try:
        run(cfg)
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
