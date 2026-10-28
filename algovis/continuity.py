"""Native, data-only artwork handoffs between independently rendered sections.

This stores painted geometry, not executable Python or a screenshot. Restored
art remains a hierarchy of selectable Manim paths and images. Use a shared
factory instead when the next section will continue editing a particular tree
or equation: a handoff preserves appearance, not the original Python class.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from manim import AnimationGroup, FadeOut, Group, ImageMobject, ManimColor, Succession, VMobject


_PAINT = ("fill_rgbas", "stroke_rgbas", "background_stroke_rgbas",
          "stroke_width", "background_stroke_width", "sheen_factor", "sheen_direction")
_METADATA = ("_algovis_label", "text", "tex_string", "_algovis_font_reference",
             "_algovis_font_container", "_algovis_type_role", "_algovis_semantic_role")


def _pack(mob):
    record = {"points": mob.points.tolist(), "z": float(mob.z_index),
              "children": [_pack(child) for child in mob.submobjects]}
    pixels = getattr(mob, "pixel_array", None)
    if isinstance(pixels, np.ndarray):
        record["image"] = {"shape": list(pixels.shape),
                           "bytes": base64.b64encode(pixels.astype(np.uint8).tobytes()).decode("ascii"),
                           "resampling": int(mob.resampling_algorithm)}
    elif isinstance(mob, VMobject):
        record["paint"] = {key: np.asarray(getattr(mob, key)).tolist() for key in _PAINT}
    elif mob.has_points():
        raise TypeError(f"Unsupported painted object in section handoff: {type(mob).__name__}")
    record["metadata"] = {key: getattr(mob, key) for key in _METADATA
                          if key in mob.__dict__}
    return record


def _unpack(record):
    if "image" in record:
        image = record["image"]
        pixels = np.frombuffer(base64.b64decode(image["bytes"]), dtype=np.uint8)
        mob = ImageMobject(pixels.reshape(image["shape"]).copy())
        mob.set_resampling_algorithm(image["resampling"])
    elif "paint" in record:
        mob = VMobject()
        for key, value in record["paint"].items():
            setattr(mob, key, np.asarray(value) if isinstance(value, list) else value)
    else:
        mob = Group()
    mob.points = np.asarray(record["points"], dtype=float).reshape((-1, 3))
    mob.z_index = record["z"]
    # Do not propagate opacity or z-index: hidden children stay hidden.
    for key, value in record["metadata"].items():
        setattr(mob, key, value)
    if "_algovis_label" not in record["metadata"]:
        for key in ("text", "tex_string"):
            if record["metadata"].get(key):
                mob._algovis_label = record["metadata"][key]
                break
    mob.add(*[_unpack(child) for child in record["children"]])
    return mob


class SectionHandoff:
    """Save a final native composition and restore it at the next clip's start."""

    @staticmethod
    def save(scene, path, *, exclude=()):
        excluded = {id(part) for root in exclude for part in root.get_family()}
        # Top-level scene ownership is authoritative; never reconstruct an
        # artificial VGroup from every descendant and draw shared glyphs twice.
        roots = [mob for mob in scene.mobjects if id(mob) not in excluded]
        camera = scene.camera
        content = {"schema": 1, "frame": [float(camera.frame_width), float(camera.frame_height)],
                   "center": np.asarray(camera.frame_center).tolist(),
                   "background": ManimColor(camera.background_color).to_hex(),
                   "objects": [_pack(mob) for mob in roots]}
        payload = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        content["fingerprint"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
        return content["fingerprint"]

    @staticmethod
    def load(scene, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Render the preceding section first: {path}")
        content = json.loads(path.read_text(encoding="utf-8"))
        fingerprint = content.pop("fingerprint")
        payload = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if content["schema"] != 1 or hashlib.sha256(payload.encode("utf-8")).hexdigest() != fingerprint:
            raise ValueError(f"Invalid section handoff: {path}")
        camera = scene.camera
        if not np.allclose(content["frame"], [camera.frame_width, camera.frame_height]):
            raise ValueError("Section handoffs require matching camera frames")
        if not np.allclose(content.get("center", [0, 0, 0]), camera.frame_center):
            raise ValueError("Section handoffs require matching camera centers")
        if content["background"] != ManimColor(camera.background_color).to_hex():
            raise ValueError("Section handoffs require matching backgrounds")
        artwork = Group(*[_unpack(record) for record in content["objects"]])
        artwork._algovis_handoff_fingerprint = fingerprint
        return artwork

    @staticmethod
    def transition(outgoing, *incoming, run_time, clear_fraction=.45):
        """Clear a genuinely different topic before its first reveal, in-slot.

        No extra preroll is inserted: word cues and the voice track keep their
        original clock. The first incoming animation must be an introductory
        reveal, not an attention effect on a retained object.
        """
        if not 0 < clear_fraction < 1 or run_time <= 0 or not incoming:
            raise ValueError("A handoff transition needs incoming content and a positive time slot")
        return Succession(FadeOut(outgoing, run_time=run_time * clear_fraction),
                          AnimationGroup(*incoming, run_time=run_time * (1-clear_fraction)),
                          run_time=run_time)
