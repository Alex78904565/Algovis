"""Inventory sizing decisions before Manim runs, including unregistered text.

This is an authoring audit, not a visual certification. Known text overrides
are errors in scene source. Mixed/unknown containers require classification;
shared diagram geometry and component-owned label policies remain separate.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import json
from pathlib import Path

TEXT = {'Text', 'MarkupText', 'Tex', 'MathTex', 'SingleStringMathTex', 'MathRow',
        'DecimalNumber', 'Integer', 'TextObject', 'Equation'}
DIAGRAMS = {'RecursiveTree', 'StateRow', 'StateCell', 'CallNode', 'CapacityChoiceStory',
            'CapacityBag', 'RoadTripStory', 'CityRouteStory', 'Axes', 'NumberLine',
            'Rectangle', 'RoundedRectangle', 'Circle', 'Dot', 'Line', 'Arrow',
            'CurvedArrow', 'Polygon', 'Square', 'ImageMobject', 'SVGMobject', 'Brace'}
SIZE_METHODS = {'scale', 'scale_to_fit_width', 'scale_to_fit_height', 'set_width',
                'set_height', 'stretch_to_fit_width', 'stretch_to_fit_height',
                'match_width', 'match_height', 'set_font_size'}
POSITION_METHODS={'move_to','next_to','align_to','shift','set_x','set_y','set_z',
                  'arrange','arrange_in_grid','to_edge','to_corner','center'}


def name(node):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute): return name(node.value) + '.' + node.attr
    return ''


def live_nodes(node):
    """Exclude statements parked after an unconditional return/raise."""
    yield node
    for _field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for child in value:
                if isinstance(child, ast.AST):
                    yield from live_nodes(child)
                    if isinstance(child, (ast.Return, ast.Raise)): break
        elif isinstance(value, ast.AST):
            yield from live_nodes(value)


class Source:
    def __init__(self, text, path='<source>'):
        self.text, self.path = text, str(path)
        self.tree = ast.parse(text)
        self.parents = {child: parent for parent in ast.walk(self.tree) for child in ast.iter_child_nodes(parent)}
        self.definitions = {}
        self.classes = {}
        self.aliases = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names: self.aliases[alias.asname or alias.name] = alias.name
            if isinstance(node, ast.ClassDef): self.classes[node.name] = node
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.definitions[self.owner(node, include_self=True)] = node
        self.bindings = defaultdict(lambda: defaultdict(list))
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, (ast.Name, ast.Attribute)):
                        self.bindings[self.owner(node)][name(target)].append(node.value)

    def owner(self, node, include_self=False):
        parts = []
        if not include_self: node = self.parents.get(node)
        while node is not None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): parts.append(node.name)
            node = self.parents.get(node)
        return '.'.join(reversed(parts))

    def symbol(self, node):
        raw = name(node).split('.')[-1]
        return self.aliases.get(raw, raw)

    def kind(self, node, scope, seen=()):
        if isinstance(node, ast.Call):
            symbol = self.symbol(node.func)
            if symbol in TEXT: return 'text'
            if symbol in DIAGRAMS: return 'diagram'
            if symbol in ('VGroup', 'Group'):
                kinds = {self.kind(arg, scope, seen) for arg in node.args}
                return next(iter(kinds)) if len(kinds) == 1 else 'mixed_or_unknown'
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ('math', 'math_like', 'text', 'next_layout', 'part', 'get_part_by_tex'):
                    return 'text'
                if node.func.attr == 'watch' and len(node.args) > 1:
                    return self.kind(node.args[1], scope, seen)
                return self.kind(node.func.value, scope, seen)
        if isinstance(node, (ast.Name, ast.Attribute)):
            key = name(node)
            if (scope, key) in seen: return 'mixed_or_unknown'
            for context in [scope, *['.'.join(scope.split('.')[:i]) for i in range(len(scope.split('.'))-1, -1, -1)]]:
                values = self.bindings[context].get(key)
                if values:
                    kinds = {self.kind(value, context, (*seen, (scope, key))) for value in values}
                    return next(iter(kinds)) if len(kinds) == 1 else 'mixed_or_unknown'
        return 'mixed_or_unknown'

    def method(self, class_name, method, seen=()):
        if class_name in seen: return None
        key = class_name + '.' + method
        if key in self.definitions: return key
        cls = self.classes.get(class_name)
        if cls:
            for base in cls.bases:
                found = self.method(name(base), method, (*seen, class_name))
                if found: return found
        return None

    def reachable(self, class_name):
        """Conservative in-file call graph; imported components audited separately."""
        first = self.method(class_name, 'construct')
        if first is None: raise ValueError(f'Cannot locate {class_name}.construct in {self.path}')
        pending, visited = [first], set()
        while pending:
            key = pending.pop()
            if key in visited: continue
            visited.add(key)
            for call in live_nodes(self.definitions[key]):
                if not isinstance(call, ast.Call): continue
                func = name(call.func)
                if func.startswith('self.'):
                    target = self.method(class_name, func[5:])
                else:
                    target = func if func in self.definitions else None
                    if target is None:
                        nested = key + '.' + func
                        if nested in self.definitions: target = nested
                if target and target not in visited: pending.append(target)
        # Nested callbacks may execute through higher-order component factories.
        return {key for key in self.definitions if any(key == parent or key.startswith(parent+'.') for parent in visited)}

    def findings(self):
        found = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr in ('font_size', 'width', 'height'):
                        scope = self.owner(node)
                        kind = self.kind(target.value, scope)
                        category = 'absolute_font_size' if target.attr == 'font_size' else (
                            'manual_text_scale' if kind == 'text' else 'container_size_review')
                        found.append(self.record(node, scope, category, kind, target.attr+'='+ast.unparse(node.value)))
            if not isinstance(node, ast.Call): continue
            scope = self.owner(node)
            symbol = self.symbol(node.func)
            if isinstance(node.func, ast.Attribute) and symbol in SIZE_METHODS:
                kind = self.kind(node.func.value, scope)
                category = 'manual_text_scale' if kind == 'text' else 'container_size_review'
                found.append(self.record(node, scope, category, kind, symbol))
            for keyword in node.keywords:
                if keyword.arg == 'font_size':
                    kind = 'text' if symbol in TEXT else self.kind(node, scope)
                    found.append(self.record(node, scope, 'absolute_font_size', kind, ast.unparse(keyword.value)))
            if symbol in ('add', 'set_font_scale'):
                factor = next((kw.value for kw in node.keywords if kw.arg == 'font_scale'), None)
                if symbol == 'set_font_scale' and len(node.args) > 1: factor = node.args[1]
                if factor is not None:
                    found.append(self.record(node, scope, 'relative_font_override', 'text', ast.unparse(factor)))
        return sorted(found, key=lambda record: (record['line'], record['category']))

    def record(self, node, scope, category, kind, operation):
        lines = self.text.splitlines()
        return {'path': self.path, 'line': node.lineno, 'owner': scope,
                'category': category, 'subject': kind, 'operation': operation,
                'source': lines[node.lineno-1].strip(),
                'disposition': 'relative_override_review' if category == 'relative_font_override' else
                               'component_geometry_review' if kind == 'diagram' else
                               'migration_required' if category in ('manual_text_scale', 'absolute_font_size') and kind == 'text' else
                               'classification_required'}


def audit_source(text, *, path='<source>', scene=None):
    source = Source(text, path)
    reachable = source.reachable(scene) if scene else None
    findings = source.findings()
    if reachable is not None:
        lines = {node.lineno for key in reachable for node in live_nodes(source.definitions[key])
                 if isinstance(node, (ast.Call, ast.Assign, ast.AnnAssign))}
        findings = [record for record in findings if record['owner'] in reachable and record['line'] in lines]
    return {'path': str(path), 'scene': scene, 'reachableFunctions': sorted(reachable) if reachable is not None else None,
            'findings': findings, 'counts': dict(Counter(record['category'] for record in findings)),
            'compliant': not findings,
            'scope': 'Static sizing-call inventory. Geometry and relative overrides require explicit classification. No render or visual signoff.'}


def require_scene_typography(path, scene):
    """Reject known manual text sizing without relying on opt-in peer tags."""
    path = Path(path)
    report = audit_scene_project(path, scene)
    problems = [record for record in report['findings'] if record['category'] in
                ('absolute_font_size','manual_text_scale','container_size_review','manual_scene_placement')]
    if problems:
        details = '; '.join(f"{record['owner']}:{record['line']} {record['category']}" for record in problems[:5])
        raise ValueError(f'Scene typography migration required ({len(problems)} manual text sizing decisions): {details}. '
                         'Use scene defaults and declared relative font scales; the previous preview remains available.')
    return report


def audit_scene_project(path, scene):
    """Include local authoring imports, so a small entrypoint cannot hide sizing.

    Shared library modules have their own component-policy audit. Every imported
    authoring module is conservatively inventoried in full, including callbacks
    and builder functions invoked through an alias. No imports are executed.
    """
    path=Path(path).resolve()
    root=next((parent for parent in path.parents if (parent/'algovis').is_dir()),path.parent)
    pending=[(path,scene)];seen=set();reports=[]
    while pending:
        current,entry=pending.pop()
        if current in seen:continue
        seen.add(current)
        content=current.read_text(encoding='utf-8-sig')
        module_report=audit_source(content,path=str(current),scene=entry)
        reports.append(module_report)
        tree=ast.parse(content)
        # Layout belongs to shared scenes/components. Moving a container or a
        # helper-returned equation is just as manual as moving raw MathTex.
        source=Source(content,str(current))
        active=set(source.reachable(entry)) if entry else None
        placements=[source.record(node,source.owner(node),'manual_scene_placement',
                    source.kind(node.func.value,source.owner(node)),node.func.attr)
            for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
            and node.func.attr in POSITION_METHODS and (active is None or source.owner(node) in active)]
        module_report['findings'].extend(placements)
        for node in ast.walk(tree):
            modules=[]
            if isinstance(node,ast.Import):modules=[alias.name for alias in node.names]
            elif isinstance(node,ast.ImportFrom):
                if node.level:
                    base=current.parent
                    for _ in range(node.level-1):base=base.parent
                    try:prefix='.'.join(base.relative_to(root).parts)
                    except ValueError:continue
                    module='.'.join(part for part in (prefix,node.module) if part)
                else:module=node.module or ''
                modules=[module,*[module+'.'+alias.name for alias in node.names]]
            for module in modules:
                if module.split('.')[0] in ('algovis','manim','numpy'):continue
                candidate=root.joinpath(*module.split('.'))
                for imported in (candidate.with_suffix('.py'),candidate/'__init__.py'):
                    if imported.is_file() and imported not in seen:pending.append((imported,None))
    findings=[finding for report in reports for finding in report['findings']]
    return {'path':str(path),'scene':scene,'modules':reports,'findings':findings,
            'counts':dict(Counter(item['category'] for item in findings)),
            'compliant':not findings,
            'scope':'Entry scene and all local authoring imports; shared component policies audited separately. No visual signoff.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', nargs='+', type=Path)
    parser.add_argument('--scene')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    reports = [audit_source(path.read_text(encoding='utf-8-sig'), path=str(path), scene=args.scene) for path in args.sources]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2), encoding='utf-8')
    for report in reports: print(report['path'], report['counts'])
    return 1 if any(report['findings'] for report in reports) else 0


if __name__ == '__main__': raise SystemExit(main())
