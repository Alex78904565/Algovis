# Audit sizing before rendering

Compiling every animation through the view infrastructure does not establish
that its artwork uses automatic layout or typography. `CanvasSlide` retains
prepared component geometry. `FitPolicy` fits the sizes supplied by its caller;
it does not turn independently sized text fragments into one coherent equation.
The earlier view migration left these separate authoring concerns unresolved.

The intended contract remains:

- The scene supplies default heading, body, equation and label sizes.
- Peer expressions are constructed from the same equation model and type role.
- Deliberate hierarchy changes use a relative font scale with a clear reason.
- Components own diagram geometry and their internal label policy.
- Operators belong to the equation's typography contract too.

`LessonStyle.watch` registers a diagnostic peer relationship. It does not assign
a scene's default size, prohibit scaling, or certify unregistered neighboring
objects. Existing automatic views preserve the caller's natural font size before
fitting. These limitations must be addressed during the typography migration;
do not present an opt-in peer check or a view-compiled timeline as that migration.

## Source inventory

Run the audit against an entry scene and its in-file helpers:

```powershell
python -m algovis.review.typography_source lesson.py --scene Lesson --output .qa/typography-source.json
```

Omit `--scene` to inventory the whole file. Multiple source paths are accepted.
The output records owner, line, category, inferred subject and original source.
The command exits nonzero while sizing decisions remain undispositioned; it does
not certify a visual result.

The inventory distinguishes manual text scaling, absolute font-size arguments,
container/diagram geometry, and explicit relative overrides. Type inference follows
ordinary assignments, constructor aliases and text-only groups. The scene call
graph follows inherited methods and local helpers; code parked after an
unconditional return is excluded. Imported component implementations need their
own inventory. Unknown containers remain explicitly unclassified. Dynamic Python
execution means a static call graph is conservative, not complete execution proof.

The reviewer checks known manual text sizing before launching Manim when its
source and entry scene are configured. This check does not depend on `watch`
registration. A rejected attempt retains the previous published preview. Use
`--source lesson.py` or a catalog's `source` field. The supported legacy production
launcher is also checked against its `full_video_preview.py`. A different custom
launcher without a configured source does not provide source-audit coverage. The
agent must inventory that gap rather than silently call it a successful check.

## Migration and verification

An audit finding is not automatically a visible defect. An array, route map or
tree needs component-owned geometry. Test fixtures deliberately exercise invalid
sizes. Inventory these separately from ordinary scene text and equations.

Do not mechanically replace hundreds of `scale` calls with `font_scale` calls.
That would preserve the unexplained exceptions. Establish shared scene type roles,
normalize ordinary incoming text, and replace separately constructed peer rows
with copies/refinements of the same named equation. Review each remaining relative
exception for its instructional purpose. Track unresolved migration work explicitly.

After changing artwork, rebuild the affected sections. Inspect the actual encoded
font sizes, baselines, spacing, copy motion and section joins. An intentional
destination-format change must finish during travel, before landing. Reassemble
the complete previews only after those checks. A source audit alone cannot justify
claiming that the existing videos were repaired or visually rechecked.
