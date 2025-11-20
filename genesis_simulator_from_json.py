#!/usr/bin/env python3
import json, argparse, os, sys, time
import genesis as gs

# ---------- Helpers ----------
_MATERIAL_ALIASES = {
    "youngs_modulus": "E",
    "poisson_ratio": "nu",
    "density": "rho",
}
def _apply_aliases(d, aliases):
    return {aliases.get(k, k): v for k, v in d.items()}

def make_mpm_material(spec: dict):
    kind = spec.get("type", "Elastic").lower()
    params = {k: v for k, v in spec.items() if k != "type"}
    # allow descriptive keys for Elastic
    if kind == "elastic":
        params = _apply_aliases(params, _MATERIAL_ALIASES)
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
    kind = spec.get("type", "Box").lower()
    params = {k: v for k, v in spec.items() if k != "type"}
    if kind == "box": return gs.morphs.Box(**params)
    if kind == "sphere": return gs.morphs.Sphere(**params)
    if kind == "plane": return gs.morphs.Plane(**params)
    if kind == "mesh": return gs.morphs.Mesh(**params)  # expects path/pos/rot/scale
    raise ValueError(f"Unknown morph type: {spec.get('type')}")

def make_surface(spec: dict | None):
    if not spec: return gs.surfaces.Default()
    kind = spec.get("type", "Default")
    params = {k: v for k, v in spec.items() if k != "type"}
    return getattr(gs.surfaces, kind, gs.surfaces.Default)(**params)

# ---------- Scene builder ----------
def build_scene(cfg: dict):
    gs.init()
    sim_opt = cfg.get("sim_options", {})
    mpm_opt = cfg.get("mpm_options", {})
    vis_opt = cfg.get("vis_options", {})
    viewer_opt = cfg.get("viewer_options", {})
    show_viewer = bool(cfg.get("show_viewer", True))

    # allow particle_radius alias -> particle_size (diameter)
    if "particle_radius" in mpm_opt and "particle_size" not in mpm_opt:
        mpm_opt["particle_size"] = 2.0 * float(mpm_opt.pop("particle_radius"))

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(**sim_opt),
        mpm_options=gs.options.MPMOptions(**mpm_opt),
        vis_options=gs.options.VisOptions(**vis_opt),
        viewer_options=gs.options.ViewerOptions(**viewer_opt),
        show_viewer=show_viewer
    )

    # static geometry
    for ent in cfg.get("static", []):
        morph = make_morph(ent["morph"])
        surface = make_surface(ent.get("surface"))
        name = ent.get("name", "static")
        scene.add_entity(morph=morph, surface=surface)
        print(f"[add] static: {name}")

    # mpm bodies
    mpm_entities = []
    bodies_spec = cfg.get("mpm_bodies", [])
    max_bodies = int(cfg.get("max_bodies", len(bodies_spec)))
    for i, ent in enumerate(bodies_spec[:max_bodies]):
        material = make_mpm_material(ent["material"])
        morph = make_morph(ent["morph"])
        surface = make_surface(ent.get("surface"))
        name = ent.get("name", f"mpm_{i}")
        e = scene.add_entity(material=material, morph=morph, surface=surface)
        mpm_entities.append((name, e))
        print(f"[add] mpm body: {name}")

    scene.build()
    return scene, mpm_entities

# ---------- Simulation ----------
def run(cfg: dict):
    scene, bodies = build_scene(cfg)
    nsteps = int(cfg.get("steps", 600))
    capture = cfg.get("capture", {})
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
            path = os.path.join(capture_dir, f"frame_{step:05d}.png")
            try:
                scene.viewer.screenshot(path)
            except Exception:
                pass
    print(f"[done] {nsteps} steps in {time.time()-t0:.2f}s")

    if dump_particles and bodies:
        for name, b in bodies:
            try:
                pts = b.get_particles()
                print(f"[particles] {name}: {len(pts)}")
            except Exception:
                print(f"[particles] {name}: not available on this backend")

def main():
    ap = argparse.ArgumentParser(description="Genesis MPM from JSON")
    ap.add_argument("-c", "--config", required=True)
    args = ap.parse_args()
    with open(args.config, "r") as f:
        cfg = json.load(f)
    try:
        run(cfg)
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
