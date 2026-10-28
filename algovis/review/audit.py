"""Word-level animation timing and composition-change ledgers.

An inherited scene cue is context, not proof of an animation's spoken trigger.
Attention effects require their own declared phrase. The report is an agent's
worklist; generated output and a passing unit suite are not editorial signoff.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from .inspection import semantic_objects, typography_findings, alignment_findings

ATTENTION = {"Pulse", "Indicate", "Circumscribe", "ShowPassingFlash", "Flash",
             "Highlight", "FocusOn", "Wiggle"}
NUMBERS = {str(i): word for i, word in enumerate(
    ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
     "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
     "eighteen", "nineteen", "twenty"))}


def tokens(text):
    text = str(text).lower().replace("’", "'")
    # ASR may split a hyphenated spoken word into "long", "-term".
    # This is a word continuation, not a spoken minus operator. Keep the
    # exception narrow so mathematical negative numbers still require minus.
    if text.strip() in {"-term", "-down", "-up"}:
        text = text.replace("-", "", 1)
    text = re.sub(r"\b([vw])_?i\b", r"\1 i", text)
    text = re.sub(r"([a-z]{2,})-([a-z]{2,})", r"\1 \2", text)
    text = re.sub(r"\b([fghpq])\s*[\[(]([^\])]+)[\])]", r"\1 of \2", text)
    for compound, separated in (("longterm", "long term"), ("topdown", "top down"),
                                ("bottomup", "bottom up")):
        text = re.sub(r"\b"+compound+r"\b", separated, text)
    text = re.sub(r"\\(?:text|mathrm|operatorname|mathbf)\{([^{}]*)\}", r" \1 ", text)
    text = text.replace("+", " plus ").replace("-", " minus ")
    return [NUMBERS.get(word, word) for word in re.findall(r"[a-z]+|\d+", text)]


def timed_words(document):
    words = document.get("words") or [word for segment in document.get("segments", [])
                                     for word in segment.get("words", [])]
    unique = {(float(w["start"]), float(w["end"]), w["word"]): w for w in words}
    return sorted(unique.values(), key=lambda w: (w["start"], w["end"]))


def phrase_anchor(phrase, words, near):
    wanted = tokens(phrase)
    if not wanted:
        return None
    expanded = [(token, index) for index, word in enumerate(words) for token in tokens(word["word"])]
    text = [token for token, _index in expanded]
    matches = []
    for index in range(len(text)-len(wanted)+1):
        if text[index:index+len(wanted)] != wanted:
            continue
        indices = sorted({word_index for _token, word_index in expanded[index:index+len(wanted)]})
        selected = [words[word_index] for word_index in indices]
        matches.append({"start": selected[0]["start"], "end": selected[-1]["end"],
                        "words": selected, "approximate": any(
                            word.get("reviewed_timing") == "approximate" for word in selected)})
    return min(matches, key=lambda match: abs(match["start"]-near)) if matches else None


def content_change(before, after):
    old, new = {obj["id"]: obj for obj in before}, {obj["id"]: obj for obj in after}
    removed = [obj for key, obj in old.items() if key not in new]
    added = [obj for key, obj in new.items() if key not in old]
    retained = [obj for key, obj in new.items() if key in old]
    return {"removed": removed, "added": added, "retained": retained,
            "retainedFraction": len(retained)/len(old) if old else 1.0}


def audit_section(manifest, cue_document, transcript, *, attention_tolerance=None):
    words = timed_words(transcript)
    cues = {cue["name"]: cue for cue in cue_document.get("cues", [])}
    fps = float(manifest.get("frameRate", 15))
    tolerance = attention_tolerance if attention_tolerance is not None else 1/fps+.015
    events, findings = [], []
    for original in manifest.get("animations", []):
        event = dict(original)
        start, end = float(event["start"]), float(event["end"])
        cue = cues.get(event.get("cue"), {})
        metadata = event.get("attention") or {}
        timing = event.get("wordTiming") or {}
        explicit = metadata.get("trigger") or timing.get("trigger")
        context_phrase = cue.get("phrase", "")
        offset = float(timing.get("narrationStart", 0))
        anchor = phrase_anchor(explicit or context_phrase, words, start-offset)
        if anchor and offset:
            anchor = {**anchor, "start":anchor["start"]+offset, "end":anchor["end"]+offset}
        event.update({"duration": end-start, "contextPhrase": context_phrase,
                      "triggerPhrase": explicit, "anchor": anchor,
                      "wordOffset": start-anchor["start"] if anchor else None,
                      "spokenDuring": [word for word in words if word["end"]+offset>start and word["start"]+offset<end],
                      "findings": []})
        if event.get("kind") in ATTENTION:
            if not explicit:
                event["findings"].append("attention_without_declared_trigger")
            elif anchor is None:
                event["findings"].append("trigger_not_found_in_words")
            elif anchor["approximate"]:
                event["findings"].append("trigger_word_timing_is_approximate")
            elif abs(start-anchor["start"]) > tolerance:
                event["findings"].append("attention_before_word" if start<anchor["start"] else "attention_after_word")
        for finding in event["findings"]:
            findings.append({"kind": finding, "event": event["id"], "time": start,
                             "cue": event.get("cue"), "target": event.get("label")})
        events.append(event)

    plays = list(manifest.get("plays", []))
    if not plays:
        # Old manifests can still be inspected, but must never masquerade as
        # having passed the new identity-preservation checks.
        findings.append({"kind": "missing_before_after_provenance", "time": 0})
        snapshots = manifest.get("snapshots", [])
        grouped = defaultdict(list)
        for event in events:
            grouped[event["play"]].append(event)
        for _play, group in sorted(grouped.items()):
            start, end = min(e["start"] for e in group), max(e["end"] for e in group)
            before = max((s for s in snapshots if s["time"]<=start+.001),
                         key=lambda s:s["time"], default={})
            after = min(snapshots, key=lambda s:abs(s["time"]-end), default={})
            plays.append({"start":start,"end":end,"cue":group[0].get("cue"),
                          "before":semantic_objects(before),"after":semantic_objects(after),
                          "source":group[0].get("source", {})})

    changes, removed_history = [], []
    for index, play in enumerate(plays):
        if not any(event['start'] < play['end']-.0001 and
                   event['end'] > play['start']+.0001 for event in events):
            # Manim implements waits as plays too. A still hold is timing
            # space, not another composition change for the agent to audit.
            continue
        play = dict(play)
        # Early instrumented renders stored whole snapshots; current renders
        # store the same semantic leaves directly. Audit both, without treating
        # the snapshot dictionary's keys as object records.
        for side in ("before", "after"):
            if isinstance(play.get(side), dict):
                play[side] = semantic_objects(play[side])
        change = {**play, **content_change(play.get("before", []), play.get("after", [])),
                  "id":f"change-{index+1:04d}", "findings": []}
        timing = play.get("wordTiming")
        if timing:
            offset = float(timing.get("narrationStart", 0))
            anchor = phrase_anchor(timing.get("trigger", ""), words, play["start"]-offset)
            if anchor is None or anchor["approximate"]:
                change["findings"].append("content_without_verified_word")
            elif abs(play["start"]-anchor["start"]-offset) > tolerance:
                change["findings"].append(
                    "content_before_word" if play["start"]<anchor["start"]+offset else "content_after_word"
                )
        if len(change["before"]) >= 4 and change["retainedFraction"] < .45:
            change["findings"].append("large_content_clear")
        candidates = removed_history + [(play["start"], obj) for obj in change["removed"]]
        reintroduced = []
        for added in change["added"]:
            label = "".join(tokens(added["label"]))
            if len(label) < 8:
                continue
            matches = [(time, old) for time,old in candidates if
                       play["start"]-time <= 120 and old["id"]!=added["id"]
                       and "".join(tokens(old["label"])) == label]
            if matches:
                time, old = max(matches,key=lambda pair:pair[0])
                reintroduced.append({"label":added["label"],"oldId":old["id"],
                                     "newId":added["id"],"removedAt":time})
        if reintroduced:
            change["findings"].append("content_erased_then_recreated")
        change["reintroduced"] = reintroduced
        removed_history.extend((play["start"], obj) for obj in change["removed"])
        for finding in change["findings"]:
            findings.append({"kind":finding,"change":change["id"],"time":play["start"],
                             "cue":play.get("cue"),"source":play.get("source",{})})
        changes.append(change)
    # Explicit peer groups make type-size regressions mechanically detectable.
    # Report the first occurrence of each mismatch, not the same flag per hold.
    seen_type = set()
    for snapshot in manifest.get("snapshots", []):
        for finding in typography_findings(snapshot) + alignment_findings(snapshot):
            signature = (finding["kind"], finding["group"], finding.get("typeRole"),
                         tuple((o["id"],o.get("fontSize"),o.get("left")) for o in finding["objects"]))
            if signature not in seen_type:
                seen_type.add(signature)
                findings.append(finding)
    return {"events":events,"changes":changes,"findings":findings,
            "wordCount":len(words), "frameTolerance":tolerance,
            "status":"requires_agent_review" if findings else "automated_checks_passed"}


def _text(value):
    return str(value or "—").replace("|", "\\|").replace("\n", " ")


def markdown_report(section, report):
    lines = [f"# {section['title']} — word-level animation ledger", "",
             "This is the agent's audit worklist. An inherited cue is context, not an approved trigger.",
             "A passing automated check does not replace inspecting the rendered frames.", "",
             f"Status: **{report['status']}**. {len(report['events'])} events; {len(report['findings'])} findings.", "",
             "## Actual animation intervals", "",
             "| Start–end (s) | Duration | Kind / target | Declared trigger | Word start | Offset | Source | Findings |",
             "|---|---:|---|---|---:|---:|---|---|"]
    word_lines = ["", "## Words during each event", ""]
    for event in report['events']:
        anchor = event['anchor'];source=event.get('source',{})
        lines.append(f"| {event['start']:.3f}–{event['end']:.3f} | {event['duration']:.3f} | "
                     f"{_text(event['kind'])}: {_text(event.get('label'))} | "
                     f"{_text(event.get('triggerPhrase') or ('context: '+event['contextPhrase']))} | "
                     f"{anchor['start'] if anchor else 'unmatched'} | "
                     f"{round(event['wordOffset'],3) if event['wordOffset'] is not None else '—'} | "
                     f"{_text(source.get('file'))}:{source.get('line','?')} | {_text(', '.join(event['findings']))} |")
        spoken = " ".join(f"{w['word'].strip()} [{w['start']:.3f}–{w['end']:.3f}]" for w in event['spokenDuring'])
        if spoken:
            word_lines.append(f"- `{event['id']}`: {spoken}")
    lines.extend(word_lines)
    lines.extend(["", "## Composition continuity", ""])
    for change in report['changes']:
        lines.extend([f"### {change['start']:.3f}–{change['end']:.3f} · {change.get('cue')}", "",
                      f"Retained: {change['retainedFraction']:.0%}. Findings: {', '.join(change['findings']) or 'none'}.",
                      "", "- Kept: "+_text('; '.join(o['label'] for o in change['retained'])),
                      "- Removed: "+_text('; '.join(o['label'] for o in change['removed'])),
                      "- Added: "+_text('; '.join(o['label'] for o in change['added'])), ""])
    return "\n".join(lines)+"\n"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=Path.cwd())
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--section', action='append', default=[])
    args=parser.parse_args();root=args.workspace.resolve()
    catalog=json.loads((root/args.catalog).read_text(encoding='utf-8'))
    output=root/args.output;output.mkdir(parents=True,exist_ok=True);summary={}
    for section in catalog['sections']:
        sid=section['id'];manifest=root/section.get('manifest',f'.review/manifests/{sid}.objects.json')
        if args.section and sid not in args.section:
            continue
        if not manifest.exists():
            summary[sid]={'status':'missing_render_manifest'};continue
        paths=[manifest,root/section['cues'],root/section['transcriptWords']]
        documents=[json.loads(path.read_text(encoding='utf-8')) for path in paths]
        report=audit_section(*documents)
        report['inputs']={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        (output/(sid+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        (output/(sid+'.md')).write_text(markdown_report(section,report),encoding='utf-8')
        summary[sid]={'status':report['status'],'events':len(report['events']),
                      'findings':len(report['findings'])}
        print(sid,summary[sid],flush=True)
    (output/'index.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    index_lines = ['# Animation audit ledgers', '',
                   'These reports are for the agent to inspect and repair before requesting viewer review.', '',
                   '| Section | Actual events | Internal findings | Ledger |',
                   '|---|---:|---:|---|']
    for sid, item in summary.items():
        index_lines.append(f"| {sid} | {item.get('events',0)} | {item.get('findings',0)} | [{sid}]({sid}.md) |")
    (output/'index.md').write_text('\n'.join(index_lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
