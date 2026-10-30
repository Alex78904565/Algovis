"""Plan fitting over a complete explanation, before its first visible step."""
from dataclasses import replace
from .composition import ProofSlide


def natural_view(view):
    result=view.snapshot()
    for field in ('_sequence_layout_name','_sequence_fit_scales','_sequence_proof_envelopes'):
        result.__dict__.pop(field,None)
    for item in result.items.values():
        if item.fit_scale!=1:result._scale_item(item,1/item.fit_scale)
        item.fit_scale=1.
        item.target._algovis_view_fit_scale=1.
    return result


def plan_sequence(name,views):
    """One type scale and one proof-row envelope for every planned scene.

    Invisible future rows reserve space through their measured geometry; they
    are never inserted into an earlier scene's visible objects. A layout that
    cannot fit readably fails here, before any member begins playback.
    """
    planned=[natural_view(view) for view in views]
    envelopes={};scales={}
    proofs=[view for view in planned if isinstance(view,ProofSlide)]
    for view in proofs:
        for slot,row in view.row_envelopes().items():
            shared=envelopes.setdefault(slot,dict(height=0.,ascent=0.,descent=0.))
            for metric,value in row.items():shared[metric]=max(shared[metric],value)
    for row in envelopes.values():row['height']=max(row['height'],row['ascent']+row['descent'])
    for view in proofs:
        view._sequence_proof_envelopes=envelopes
        available=view.layout.body.height-view.row_gap*(len(envelopes)-1)
        scales['body']=min(scales.get('body',1.),available/sum(row['height'] for row in envelopes.values()),1.)
    for view in planned:
        for area in view._fit_areas():
            scales[area.group]=min(scales.get(area.group,1.),area.scale(view._height))
    for view in planned:
        view._sequence_layout_name=name
        view._sequence_fit_scales=scales.copy()
        # _editing restores natural sizes before applying this one common fit.
        with view._editing():pass
    report={'name':name,'scales':scales,'proofEnvelopes':envelopes,'scenes':len(planned)}
    return planned,report
