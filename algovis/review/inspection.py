"""Visibility-aware inspection data for real Manim renders."""
from __future__ import annotations

import numpy as np
from ..layout import measured_font_size


def semantic_objects(snapshot):
    """Summarize visible text leaves once, excluding their nested containers."""
    objects = snapshot.get("objects", [])
    semantic = {obj["id"] for obj in objects if obj.get("semantic")}
    containers = {parent for obj in objects if obj["id"] in semantic
                  for parent in obj.get("parents", [])}
    return [{key: obj[key] for key in ("id", "label", "kind", "region")}
            for obj in objects if obj["id"] in semantic and obj["id"] not in containers
            and obj.get("opacity", 1) > .12]


def visible_opacity(mobject, cache=None):
    """Maximum painted opacity, ignoring zero-width strokes and hidden layers."""
    cache = {} if cache is None else cache
    identity = id(mobject)
    if identity in cache:
        return cache[identity]
    opacity = 0.0
    pixels = getattr(mobject, "pixel_array", None)
    if isinstance(pixels, np.ndarray) and pixels.ndim == 3 and pixels.shape[2] == 4:
        opacity = float(pixels[:, :, 3].max(initial=0)) / 255
    elif mobject.has_points():
        try:
            opacity = float(np.max(mobject.get_fill_opacity()))
            if float(np.max(mobject.get_stroke_width())) > 0:
                opacity = max(opacity, float(np.max(mobject.get_stroke_opacity())))
        except (AttributeError, ValueError, TypeError):
            pass
    for child in mobject.submobjects:
        opacity = max(opacity, visible_opacity(child, cache))
    cache[identity] = opacity
    return opacity


def capture_snapshot(scene, width, height):
    """Keep raw bounds and ancestry for QA; retain clipped bounds for the UI."""
    def identifier(mobject):
        identity = id(mobject)
        if identity not in scene._review_object_ids:
            scene._review_object_ids[identity] = f"object-{scene._review_next_object_id:04d}"
            scene._review_next_object_id += 1
        return scene._review_object_ids[identity]

    parents, owners, members = {}, {}, {}
    for root in scene.mobjects:
        root_id = identifier(root)
        for member in root.get_family():
            identity = id(member)
            members[identity] = member
            owners.setdefault(identity, set()).add(root_id)
            for child in member.submobjects:
                parents.setdefault(id(child), set()).add(identifier(member))

    opacity_cache = {}
    visible, offscreen = [], []
    for identity, mobject in members.items():
        opacity = visible_opacity(mobject, opacity_cache)
        if opacity <= .015:
            continue
        obj_width, obj_height = float(mobject.width), float(mobject.height)
        if obj_width < .035 or obj_height < .035:
            continue
        center = mobject.get_center()
        x = (float(center[0]) - obj_width / 2 + width / 2) / width
        y = (height / 2 - float(center[1]) - obj_height / 2) / height
        w, h = obj_width / width, obj_height / height
        left, top = max(0., x), max(0., y)
        right, bottom = min(1., x+w), min(1., y+h)
        item = {
            "id": identifier(mobject),
            "label": scene._review_object_label(mobject),
            "kind": type(mobject).__name__,
            "semantic": any(isinstance(getattr(mobject, key, None), str)
                            for key in ("_algovis_label", "text", "tex_string")),
            "opacity": round(opacity, 4),
            "parents": sorted(parents.get(identity, set())),
            "owners": sorted(owners[identity]),
            "rawRegion": {"x": x, "y": y, "width": w, "height": h},
            "region": {"x": left, "y": top, "width": max(0., right-left),
                       "height": max(0., bottom-top)},
        }
        try:
            item["color"] = mobject.get_color().to_hex()
        except (AttributeError, ValueError, TypeError):
            pass
        if item["semantic"]:
            # SVG text containers can report black while their visible glyphs
            # are white. Inspect the paint, rather than that container default.
            colors = set()
            for part in mobject.family_members_with_points():
                try:
                    if float(np.max(part.get_fill_opacity())) > .015:
                        colors.add(part.get_fill_color().to_hex())
                    if (float(np.max(part.get_stroke_width())) > 0 and
                            float(np.max(part.get_stroke_opacity())) > .015):
                        colors.add(part.get_stroke_color().to_hex())
                except (AttributeError, ValueError, TypeError):
                    pass
            item["paintColors"] = sorted(colors)
            if len(colors) == 1:
                item["color"] = next(iter(colors))
        font_size = measured_font_size(mobject)
        if isinstance(font_size, (int, float)) and np.isfinite(font_size):
            item["fontSize"] = round(float(font_size), 4)
        if getattr(mobject, "_algovis_font_container", False):
            item["fontContainer"] = True
        for attribute, key in (("_algovis_semantic_role", "semanticRole"),
                               ("_algovis_type_role", "typeRole"),
                               ("_algovis_typography_group", "typographyGroup"),
                               ("_algovis_layout", "layout"),
                               ("_algovis_layout_row", "layoutRow")):
            value = getattr(mobject, attribute, None)
            if isinstance(value, str):
                item[key] = value
        if getattr(mobject, "_algovis_alignment_owner", None) == id(mobject):
            item["alignmentGroup"] = mobject._algovis_alignment_group
        if right <= left or bottom <= top:
            offscreen.append(item)
        else:
            visible.append(item)
    return {"time": float(scene.renderer.time), "objects": visible,
            "offscreenObjects": offscreen}


def typography_findings(snapshot, *, relative_tolerance=.025):
    """Flag inconsistent sizes in explicitly declared peer groups, not headings.

    This checks actual Manim font size after scaling. Different roles (for
    example equations versus notes) form separate groups. Glyph bounds alone
    cannot compare a tall fraction with a short formula's letter size.
    """
    groups = {}
    for obj in snapshot.get("objects", []):
        if (obj.get("typographyGroup") and obj.get("fontSize", 0) > 0
                and not obj.get("fontContainer")):
            key = (obj["typographyGroup"], obj.get("typeRole", ""))
            groups.setdefault(key, []).append(obj)
    findings = []
    for (group, role), objects in groups.items():
        sizes = [obj["fontSize"] for obj in objects]
        if max(sizes)-min(sizes) > relative_tolerance*max(sizes):
            findings.append({"kind":"peer_font_size_mismatch", "time":snapshot.get("time",0),
                             "group":group, "typeRole":role,
                             "objects":[{"id":obj["id"],"label":obj["label"],"fontSize":obj["fontSize"]}
                                        for obj in objects]})
    return findings


def alignment_findings(snapshot, *, tolerance=.0035):
    """Check declared left edges in frame-relative units at settled snapshots."""
    groups = {}
    for obj in snapshot.get("objects", []):
        if obj.get("alignmentGroup") and obj.get("opacity", 1) > .12:
            groups.setdefault(obj["alignmentGroup"], []).append(obj)
    findings = []
    for group, objects in groups.items():
        lefts = [(obj.get("rawRegion") or obj["region"])["x"] for obj in objects]
        if max(lefts)-min(lefts) > tolerance:
            findings.append({"kind":"declared_left_edge_mismatch", "time":snapshot.get("time",0),
                             "group":group,"objects":[
                                 {"id":obj["id"],"label":obj["label"],"left":left}
                                 for obj,left in zip(objects,lefts)]})
    return findings
