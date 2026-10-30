"""Illustrated props with stable, cue-editable mathematical attributes."""
from uuid import uuid4
from manim import (AnimationGroup,DOWN,FadeIn,FadeOut,Group,ImageMobject,LEFT,
    RIGHT,RoundedRectangle,Transform,UP,VGroup)
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
    def __init__(self,path,label,*,theme=DEFAULT_THEME):
        self.theme=theme
        self.image=IllustrationImage(path)
        self.image.scale_to_fit_height(2.5)
        self.label=LessonStyle(theme=theme).text(label,type_role='label',role='muted')
        self.label.next_to(self.image,DOWN,buff=.15)
        super().__init__(self.image,self.label)

    def apply_scene_typography(self,typography,*,group):
        assign_scene_typography(self.label,typography,group=group,role='label')
        self.label.next_to(self.image,DOWN,buff=.15)


class IllustratedItem(Group):
    """One persistent card; numeric attributes appear on their own words."""
    def __init__(self,path,label,index,*,theme=DEFAULT_THEME):
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
        super().__init__(self.frame,self.image,self.display_name,self.weight,self.value)
        set_semantics(self,theme=theme,part='frame',channel='stroke',role='current')
        self._arrange()
        self.weight.set_opacity(0);self.value.set_opacity(0)

    def _arrange(self):
        self.image.move_to(self.frame.get_center()+UP*.38)
        self.display_name.move_to(self.frame.get_center()+DOWN*.42)
        metrics=VGroup(self.weight,self.value).arrange(RIGHT,buff=.32)
        metrics.move_to(self.frame.get_center()+DOWN*.84)

    def apply_scene_typography(self,typography,*,group):
        for part in (self.display_name,self.weight,self.value):
            assign_scene_typography(part,typography,group=group,role='label')
        self._arrange()

    def part(self,name):return getattr(self,name)

    def with_state(self,*,weight=None,value=None,show_weight=None,show_value=None):
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
        return self


class ItemCollection(Group):
    """A layout container reuses the same cards in a grid or a row."""
    _algovis_layout_container=True
    def __init__(self,*items,columns=4):
        self.columns=columns
        super().__init__(*items)

    def apply_scene_typography(self,typography,*,group):
        for item in self:assign_scene_typography(item,typography,group=group)
        self.arrange_in_grid(cols=self.columns,buff=(.28,.28))

    def part(self,name):return self[int(name)]

    def with_state(self,*,index,**state):
        target=self.copy()
        target.submobjects[index]=target[index].with_state(**state)
        return target
