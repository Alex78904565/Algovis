"""Plan fitting over a complete explanation, before its first visible step."""
from dataclasses import replace
from .composition import ProofSlide,_set_placement_fit
from .core.math_row import MathRow
from .frames import CaseEquation


def natural_view(view):
    result=view.snapshot()
    for field in ('_sequence_layout_name','_sequence_fit_scales','_sequence_proof_envelopes',
                  '_sequence_block_widths','_sequence_block_heights','_sequence_fill_widths',
                  '_sequence_paired_heights','_sequence_text_widths','_sequence_proof_label_y'):
        result.__dict__.pop(field,None)
    for item in result.items.values():
        if item.fit_scale!=1:result._scale_item(item,1/item.fit_scale)
        item.fit_scale=1.
        _set_placement_fit(item.target,1.)
    return result


def plan_sequence(name,views,*,previous=None):
    """One type scale and one proof-row envelope for every planned scene.

    Invisible future rows reserve space through their measured geometry; they
    are never inserted into an earlier scene's visible objects. A layout that
    cannot fit readably fails here, before any member begins playback.
    """
    planned=[natural_view(view) for view in views]
    text_widths={}
    if previous is not None:
        for item in previous.items.values():
            source=getattr(item.target,'_algovis_source_text',None)
            if source is not None:
                key=(id(item.object.mobject),source)
                text_widths[key]=getattr(previous,'_sequence_text_widths',{}).get(
                    key,previous._text_width(item.slot)/item.font_scale)
    for view in planned:
        for item in view.items.values():
            source=getattr(item.target,'_algovis_source_text',None)
            if source is not None:
                key=(id(item.object.mobject),source)
                width=view._text_width(item.slot)/item.font_scale
                text_widths[key]=min(text_widths.get(key,width),width)
    for view in planned:
        view._sequence_text_widths=text_widths.copy()
        view._wrap_text()
    fill_widths={}
    for view in planned:
        measure=getattr(view,'fill_widths',None)
        for key,width in (measure() if measure else {}).items():
            if width:fill_widths[key]=max(fill_widths.get(key,0.),width)
    for view in planned:
        view._sequence_fill_widths=fill_widths.copy()
        # Still measure natural artwork here. Running the fitting pass now
        # would measure already-fitted items as though they were natural, then
        # apply an incompatible common scale when _editing restores them.
        for item_name in getattr(view,'_width_fill',()) & view.items.keys():
            item=view.items[item_name]
            width=fill_widths.get(f'{type(view).__name__}/{item.slot}')
            if width:item.target.fill_width(width)
    # Reserve each retained equation's complete vertical envelope before the
    # first beat. Reserving only the total block height still lets a growing
    # equation sweep through the caption immediately below it.
    equation_rows={}
    for view in planned:
        for item in view.items.values():
            if not isinstance(item.target,(MathRow,CaseEquation)):continue
            key=id(item.object.mobject)
            row=equation_rows.setdefault(key,{'ascent':0.,'descent':0.})
            row['ascent']=max(row['ascent'],item.ascent,
                float(item.target.get_top()[1]-item.target.baseline))
            row['descent']=max(row['descent'],item.descent,
                float(item.target.baseline-item.target.get_bottom()[1]))
    for view in planned:
        for item in view.items.values():
            if id(item.object.mobject) in equation_rows:
                row=equation_rows[id(item.object.mobject)]
                item.ascent,item.descent=row['ascent'],row['descent']
    envelopes={};scales={};paired={}
    for view in planned:
        measure=getattr(view,'paired_heights',None)
        for key,height in (measure() if measure else {}).items():paired[key]=max(paired.get(key,0.),height)
    for view in planned:
        if hasattr(type(view),'paired_heights'):view._sequence_paired_heights=paired.copy()
    proofs=[view for view in planned if isinstance(view,ProofSlide)]
    for view in proofs:
        for slot,row in view.row_envelopes().items():
            shared=envelopes.setdefault(slot,dict(height=0.,ascent=0.,descent=0.))
            for metric,value in row.items():shared[metric]=max(shared.get(metric,0.),value)
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
    # Measure after common fitting, not from individual scene fits or raw text.
    # Reserve future width without inserting that future artwork into a view.
    widths={};heights={}
    for view in planned:
        measure=getattr(view,'block_widths',None)
        for key,width in (measure() if measure else {}).items():
            widths[key]=max(widths.get(key,0.),width)
        measure=getattr(view,'block_heights',None)
        for key,height in (measure() if measure else {}).items():
            heights[key]=max(heights.get(key,0.),height)
    for view in planned:
        view._sequence_block_widths=widths.copy()
        view._sequence_block_heights=heights.copy()
        with view._editing():pass
    # A spoken stage heading can precede its content. Position it from the
    # first real row, rather than from an empty region's center, so adding
    # that content cannot make the already-visible heading jump.
    label_y={}
    for view in proofs:
        for item_name,item in view.items.items():
            if item_name.startswith('label:') and item_name[6:] in view.items:
                label_y.setdefault(item.slot,float(item.target.get_y()))
    for view in proofs:
        view._sequence_proof_label_y=label_y.copy()
        with view._editing():pass
    report={'name':name,'scales':scales,'proofEnvelopes':envelopes,
            'blockWidths':widths,'blockHeights':heights,'fillWidths':fill_widths,'scenes':len(planned)}
    return planned,report
