"""Illustrated props with stable, cue-editable mathematical attributes."""
from uuid import uuid4
from PIL import Image
from manim import (AnimationGroup,DOWN,FadeIn,FadeOut,Group,ImageMobject,LEFT,
    RIGHT,RoundedRectangle,Transform,UP,VGroup,Brace,Rectangle,Cross,Succession)
from ..layout import LessonStyle,assign_scene_typography
from ..semantics import set_semantics
from ..theme import DEFAULT_THEME
from ..objects import Equation


class IllustrationImage(ImageMobject):
    """Share immutable image pixels between plans; detach before painting.

    A long preplanned explanation needs many geometry snapshots, not hundreds
    of copies of the same photograph. Opacity is copy-on-write, and a movement
    of unchanged artwork only interpolates its alpha channel.
    """
    def __init__(self,*args,**kwargs):
        self._asset_key=uuid4().hex
        self._rgb_key=None
        self._pixels_shared=False
        super().__init__(*args,**kwargs)

    def __deepcopy__(self,memo):
        for key in ('pixel_array','orig_alpha_pixel_array'):
            pixels=getattr(self,key,None)
            if pixels is not None:memo[id(pixels)]=pixels
        self._pixels_shared=True
        result=super().__deepcopy__(memo)
        result._pixels_shared=True
        return result

    def _writable_pixels(self):
        if self._pixels_shared:
            self.pixel_array=self.pixel_array.copy()
            self._pixels_shared=False

    def set_opacity(self,alpha):
        self._writable_pixels()
        return super().set_opacity(alpha)

    def set_color(self,color,alpha=None,family=True):
        self._writable_pixels()
        result=super().set_color(color,alpha,family)
        self._rgb_key=str(self.color)
        return result

    def interpolate_color(self,first,second,alpha):
        if (isinstance(first,IllustrationImage) and isinstance(second,IllustrationImage)
                and first._asset_key==second._asset_key and first._rgb_key==second._rgb_key):
            self._writable_pixels()
            self.fill_opacity=(1-alpha)*first.fill_opacity+alpha*second.fill_opacity
            self.stroke_opacity=(1-alpha)*first.stroke_opacity+alpha*second.stroke_opacity
            if self._asset_key!=first._asset_key or self._rgb_key!=first._rgb_key:
                self.pixel_array[:,:,:3]=first.pixel_array[:,:,:3]
            self.pixel_array[:,:,3]=(1-alpha)*first.pixel_array[:,:,3]+alpha*second.pixel_array[:,:,3]
            self._asset_key,self._rgb_key=first._asset_key,first._rgb_key
            return self
        self._pixels_shared=False
        return super().interpolate_color(first,second,alpha)


class IllustratedProp(Group):
    def __init__(self,path,label,*,relative_size=1.,theme=DEFAULT_THEME):
        self.theme=theme
        pixels=Image.open(path).convert('RGBA')
        bounds=pixels.getchannel('A').getbbox()
        if bounds:pixels=pixels.crop(bounds)
        import numpy as np
        self.image=IllustrationImage(np.array(pixels))
        self.image.scale_to_fit_height(2.5*relative_size)
        self.label=LessonStyle(theme=theme).text(label,type_role='label',role='muted')
        self.label.next_to(self.image,DOWN,buff=.15)
        super().__init__(self.image,self.label)

    def apply_scene_typography(self,typography,*,group):
        assign_scene_typography(self.label,typography,group=group,role='label')
        self.label.next_to(self.image,DOWN,buff=.15)


class IllustratedItem(Group):
    """One persistent card; numeric attributes appear on their own words."""
    _algovis_content_fields=('muted',)
    def __init__(self,path,label,index,*,metric_reserve=None,theme=DEFAULT_THEME):
        self.theme,self.index=theme,index
        style=LessonStyle(theme=theme)
        self.frame=RoundedRectangle(width=2.3,height=2.25,corner_radius=.1,
            color=theme.node,fill_color=theme.surface,fill_opacity=.96,stroke_width=2)
        # A frame can animate as an independent view root. Keep its opaque
        # surface behind the picture even while that ownership is dissolved.
        self.frame.set_z_index(-1)
        self.image=IllustrationImage(path)
        self.image.scale_to_fit_height(1.1)
        if self.image.width>1.6:self.image.scale_to_fit_width(1.6)
        self.display_name=style.text(label,type_role='label')
        self.weight=Equation({'symbol':rf'w_{index}'},theme=theme)
        self.value=Equation({'symbol':rf'v_{index}'},theme=theme)
        self.weight_visible=self.value_visible=False
        self.muted=False
        self.metric_reserve=dict(metric_reserve or {})
        self._metric_widths=None
        super().__init__(self.frame,self.image,self.display_name,self.weight,self.value)
        set_semantics(self,theme=theme,part='frame',channel='stroke',role='current')
        self._arrange()
        self.weight.set_opacity(0);self.value.set_opacity(0)

    def _arrange(self):
        self.image.move_to(self.frame.get_center()+UP*.38)
        self.display_name.move_to(self.frame.get_center()+DOWN*.42)
        widths=self._metric_widths or (self.weight.width,self.value.width)
        start=self.frame.get_x()-(sum(widths)+.32)/2
        for field,width in zip((self.weight,self.value),widths):
            field.shift((start-field.get_left()[0],self.frame.get_y()-.84-field.baseline,0))
            start+=width+.32

    def apply_scene_typography(self,typography,*,group):
        # Geometry belongs to the card, not to its previous containing layout.
        # Reset the natural card before the sequence applies its common fit.
        center=self.frame.get_center()
        self.frame.stretch_to_fit_width(2.3).stretch_to_fit_height(2.25).move_to(center)
        self.image.scale_to_fit_height(1.1)
        if self.image.width>1.6:self.image.scale_to_fit_width(1.6)
        for part in (self.display_name,self.weight,self.value):
            assign_scene_typography(part,typography,group=group,role='label')
        widths=[]
        for key,field in (('weight',self.weight),('value',self.value)):
            prepared=field.next_layout({**field.slot_tex,'eq':'=','value':str(self.metric_reserve.get(key,0))})
            widths.append(max(field.width,prepared.width))
        self._metric_widths=tuple(widths)
        self._arrange()

    def part(self,name):return getattr(self,name)

    def with_state(self,*,weight=None,value=None,show_weight=None,show_value=None,muted=None):
        target=self.copy();style=LessonStyle(theme=self.theme)
        for key,number,show in (('weight',weight,show_weight),('value',value,show_value)):
            old=getattr(target,key)
            if number is not None:
                symbol='w' if key=='weight' else 'v'
                replacement=old.next_layout({'symbol':rf'{symbol}_{self.index}','eq':'=','value':str(number)})
                old.adopt_layout(replacement)
                setattr(target,key+'_visible',True)
            if show is not None:setattr(target,key+'_visible',show)
            old.set_opacity(1 if getattr(target,key+'_visible') else 0)
        if muted is not None:
            target.muted=muted;opacity=.22 if muted else 1
            target.image.set_opacity(opacity);target.display_name.set_opacity(opacity)
            target.frame.set_stroke(opacity=opacity).set_fill(opacity=.96*opacity)
            target.weight.set_opacity(opacity if target.weight_visible else 0)
            target.value.set_opacity(opacity if target.value_visible else 0)
        target._arrange()
        return target

    def motions_to(self,target):
        from ..composition import _same_picture
        return [motion for old,new in zip(self.submobjects,target.submobjects)
                if not _same_picture(old,new)
                for motion in (old.motions_to(new) if isinstance(old,Equation) else [Transform(old,new)])]

    def adopt_layout(self,target):
        from ..composition import _adopt
        for live,new in zip(self.submobjects,target.submobjects):_adopt(live,new)
        self.frame,self.image,self.display_name,self.weight,self.value=self.submobjects
        self.weight_visible,self.value_visible=target.weight_visible,target.value_visible
        self.muted=target.muted
        return self


class ItemCollection(Group):
    """A layout container reuses the same cards in a grid or a row."""
    _algovis_layout_container=True
    _algovis_axis_reflow=True
    def __init__(self,*items,columns=4,count=None):
        self.columns=columns
        self.cards=list(items)
        self.count=count;self.count_brace=(Brace(Group(*items),DOWN,color=count._semantic_theme.foreground)
                                         if count is not None else None)
        super().__init__(*items)
        if count is not None:self.add(self.count_brace,self.count)

    def apply_scene_typography(self,typography,*,group):
        for item in self.cards:assign_scene_typography(item,typography,group=group)
        grid=Group(*self.cards).arrange_in_grid(cols=self.columns,buff=(.28,.28))
        if self.count is not None:
            assign_scene_typography(self.count,typography,group=group)
            self.count_brace.become(Brace(grid,DOWN,color=self.count._semantic_theme.foreground))
            self.count.next_to(self.count_brace,DOWN,buff=.1)

    def part(self,name):return self[int(name)]

    def with_state(self,*,index=None,focus=None,**state):
        target=self.copy()
        if index is not None:
            target.cards[index]=target.cards[index].with_state(**state)
            target.submobjects[index]=target.cards[index]
        if focus is not None:
            for index,card in enumerate(target.cards):
                target.cards[index]=card.with_state(muted=index!=focus)
                target.submobjects[index]=target.cards[index]
        return target


class CapacityMeter(VGroup):
    """A shared labelled capacity gauge with explicit current and maximum load."""
    _algovis_content_fields=('used','visible')
    def __init__(self,capacity='C',used=0,*,visible=False,theme=DEFAULT_THEME):
        self.theme,self.capacity,self.used,self.visible=theme,capacity,float(used),visible
        self.outline=RoundedRectangle(width=.28,height=1.9,corner_radius=.04,color=theme.muted,fill_opacity=0)
        self.fill=Rectangle(width=.16,height=.01,stroke_width=0,fill_color=theme.success,fill_opacity=0)
        numeric=isinstance(capacity,(int,float))
        self.capacity_label=Equation({'symbol':'C','eq':'=' if numeric else '',
            'capacity':str(capacity) if numeric else ''},theme=theme,role='current')
        self.readout=Equation({'used':f'{used:g}','slash':'/','capacity':str(capacity)},theme=theme)
        super().__init__(self.outline,self.fill,self.capacity_label,self.readout)
        self._arrange()

    def _arrange(self):
        ratio=self.used/self.capacity if isinstance(self.capacity,(int,float)) and self.capacity>0 else 0
        height=max(.01,(self.outline.height-.14)*ratio)
        self.fill.stretch_to_fit_height(height)
        self.fill.move_to(self.outline.get_bottom()+UP*(.07+height/2))
        self.capacity_label.next_to(self.outline,UP,buff=.12)
        self.readout.next_to(self.outline,DOWN,buff=.12)
        self.outline.set_stroke(opacity=1 if self.visible else 0).set_fill(opacity=0)
        self.fill.set_fill(opacity=.8 if self.visible and self.used else 0)
        self.capacity_label.set_opacity(int(self.visible));self.readout.set_opacity(int(self.visible))

    def apply_scene_typography(self,typography,*,group):
        for label in (self.capacity_label,self.readout):assign_scene_typography(label,typography,group=group,role='label')
        self._arrange()

    def with_state(self,*,capacity=None,used=None,visible=None):
        target=self.copy()
        if capacity is not None:target.capacity=capacity
        if used is not None:target.used=float(used)
        if isinstance(target.capacity,(int,float)) and not 0<=target.used<=target.capacity:
            raise ValueError('The stored load must fit; show a rejected attempt separately')
        if visible is not None:target.visible=visible
        numeric=isinstance(target.capacity,(int,float))
        target.capacity_label.adopt_layout(target.capacity_label.next_layout(eq='=' if numeric else '',
            capacity=str(target.capacity) if numeric else ''))
        target.readout.adopt_layout(target.readout.next_layout(used=f'{target.used:g}',capacity=str(target.capacity)))
        target._arrange()
        return target

    def motions_to(self,target):
        return [Transform(self.outline,target.outline),Transform(self.fill,target.fill),
                *self.capacity_label.motions_to(target.capacity_label),*self.readout.motions_to(target.readout)]

    def adopt_layout(self,target):
        from ..composition import _adopt
        for live,new in zip(self.submobjects,target.submobjects):_adopt(live,new)
        self.capacity,self.used,self.visible=target.capacity,target.used,target.visible
        return self


class IllustratedBag(IllustratedProp):
    """The illustrated bag retains its meter through the worked selection."""
    def __init__(self,path,label='BAG',*,relative_size=1.,theme=DEFAULT_THEME):
        super().__init__(path,label,relative_size=relative_size,theme=theme)
        self.meter=CapacityMeter(theme=theme)
        self.contents=Group()
        self._copy_sources={}
        self.copy_path_arc=-.5
        self.attempt=None
        self.attempt_source=None
        self.rejection=None
        self.add(self.meter,self.contents)

    @property
    def parts(self):
        return {'image':self.image,'label':self.label,'meter':self.meter,
                **{f'stored:{index}':image for index,image in enumerate(self.contents)},
                **({'attempt':self.attempt} if self.attempt is not None else {}),
                **({'rejection':self.rejection} if self.rejection is not None else {})}

    def part(self,name):return self.parts[name]

    def _arrange_contents(self):
        for index,image in enumerate(self.contents):
            image.scale_to_fit_height(self.image.height*.2)
            image.move_to(self.image.get_bottom()+RIGHT*((index%3-1)*self.image.width*.18)
                          +UP*self.image.height*(.25+.19*(index//3)))
        if self.attempt is not None:
            self.attempt.scale_to_fit_height(self.image.height*.3)
            self.attempt.move_to(self.image.get_center()+UP*self.image.height*.12)
            if self.rejection is not None:
                self.rejection.become(Cross(self.attempt,stroke_color=self.theme.danger,stroke_width=4))

    def apply_scene_typography(self,typography,*,group):
        super().apply_scene_typography(typography,group=group)
        self.meter.apply_scene_typography(typography,group=group)
        self.meter.next_to(self.image,RIGHT,buff=.3)
        self._arrange_contents()

    def with_state(self,*,capacity=None,used=None,show_meter=None,store=None,
                   attempt=None,reject_attempt=False,return_attempt=False,empty=False):
        target=self.copy();target.meter=target.meter.with_state(capacity=capacity,used=used,visible=show_meter)
        target.submobjects[2]=target.meter
        target.meter.next_to(target.image,RIGHT,buff=.3)
        if empty:target.contents=Group()
        if store is not None:
            from ..composition import SlideObject
            source=store if isinstance(store,SlideObject) else SlideObject(store)
            target._copy_sources[f'stored:{len(target.contents)}']=source
            target.contents.add(source.planned_mobject.copy())
        if attempt is not None:
            from ..composition import SlideObject
            source=attempt if isinstance(attempt,SlideObject) else SlideObject(attempt)
            target.attempt_source=source
            target.attempt=source.planned_mobject.copy()
            target._copy_sources['attempt']=source
        if reject_attempt:
            if target.attempt is None:raise ValueError('Reject an attempted item before returning it')
            target.rejection=Cross(target.attempt,stroke_color=self.theme.danger,stroke_width=4)
        if return_attempt:
            if target.attempt is None:raise ValueError('No attempted item to return')
            target.attempt=None;target.rejection=None
        target._arrange_contents()
        target.submobjects=[target.image,target.label,target.meter,target.contents,
                            *([target.attempt] if target.attempt is not None else []),
                            *([target.rejection] if target.rejection is not None else [])]
        return target

    def motions_to(self,target,*,skip=()):
        motions=[Transform(self.image,target.image),Transform(self.label,target.label),*self.meter.motions_to(target.meter)]
        motions.extend(Transform(image,target.contents[index]) if index<len(target.contents) else FadeOut(image)
                       for index,image in enumerate(self.contents) if f'stored:{index}' not in skip)
        motions.extend(FadeIn(image) for index,image in enumerate(target.contents)
                       if index>=len(self.contents) and f'stored:{index}' not in skip)
        if self.attempt is not None:
            if target.attempt is not None:motions.append(Transform(self.attempt,target.attempt))
            else:
                motions.append(Succession(Transform(self.attempt,self.attempt_source.mobject.copy()),FadeOut(self.attempt)))
        elif target.attempt is not None and 'attempt' not in skip:motions.append(FadeIn(target.attempt))
        if self.rejection is not None:
            motions.append(Transform(self.rejection,target.rejection) if target.rejection is not None else FadeOut(self.rejection))
        elif target.rejection is not None:motions.append(FadeIn(target.rejection))
        return motions

    def adopt_layout(self,target):
        from ..composition import _adopt
        for live,new in zip(self.submobjects[:3],target.submobjects[:3]):_adopt(live,new)
        contents=[]
        for index,image in enumerate(target.contents):
            live=self.contents[index] if index<len(self.contents) else image
            _adopt(live,image);contents.append(live)
        self.contents.submobjects=contents
        self.attempt=target.attempt
        self.attempt_source=target.attempt_source
        self.rejection=target.rejection
        self.submobjects=[self.image,self.label,self.meter,self.contents,
                         *([self.attempt] if self.attempt is not None else []),
                         *([self.rejection] if self.rejection is not None else [])]
        self._copy_sources={}
        return self
