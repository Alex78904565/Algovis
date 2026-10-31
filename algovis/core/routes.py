"""City maps and concrete route simulations, independent of lesson narration."""
import math
import numpy as np
from manim import (AnimationGroup,BackgroundRectangle,Circle,Create,DOWN,FadeIn,
    LEFT,Line,MoveAlongPath,RIGHT,RoundedRectangle,Transform,UP,VGroup,VectorizedPoint)
from ..layout import LessonStyle,assign_scene_typography
from ..objects import Equation
from ..theme import DEFAULT_THEME


class RouteTrace(VGroup):
    """A fully reserved route/cost line, revealed one visited city at a time."""
    def __init__(self,city_map,cities,distances,*,evaluation=None,theme=DEFAULT_THEME):
        from ..composition import SlideObject
        self.map_ref=SlideObject(city_map)
        self.cities_path=tuple(cities);self.progress=0
        self.evaluation=evaluation
        self.route=Equation({'start':str(cities[0]),**{f'edge{index}':rf'\to {city}'
            for index,city in enumerate(cities[1:])}},theme=theme)
        costs=[distances[tuple(sorted((a-1,b-1)))] for a,b in zip(cities,cities[1:])]
        self.cost=Equation({**{f'cost{index}':('+' if index else '')+str(cost)
            for index,cost in enumerate(costs)},'total':'='+str(sum(costs))},theme=theme)
        self.theme=theme
        super().__init__(self.route,self.cost)
        self.arrange(RIGHT,buff=.4)
        for key,part in self.route.parts.items():
            if key!='start':part.set_opacity(0)
        for part in self.cost.parts.values():part.set_opacity(0)

    def apply_scene_typography(self,typography,*,group):
        center=self.get_center()
        for row in (self.route,self.cost):assign_scene_typography(row,typography,group=group)
        self.arrange(RIGHT,buff=.4).move_to(center)

    def advance(self):
        index=self.progress
        start,end=self.cities_path[index:index+2]
        self.progress+=1
        route=self.route.part(f'edge{index}');cost=self.cost.part(f'cost{index}')
        route.set_opacity(1);cost.set_opacity(1)
        return AnimationGroup(self.map_ref.mobject.route_step(start-1,end-1,evaluation=self.evaluation),
            FadeIn(route),FadeIn(cost),lag_ratio=0)

    def finish_total(self):
        total=self.cost.part('total');total.set_opacity(1)
        return FadeIn(total)


class CityMap(VGroup):
    """A line of stops or a small distance network with clear edge labels."""
    def __init__(self,labels,*,distances=None,layout='line',prices=None,show_roads=True,theme=DEFAULT_THEME):
        if layout not in ('line','network'):raise ValueError('City layout must be line or network')
        self.theme,self.layout_kind=theme,layout
        style=LessonStyle(theme=theme)
        count=len(labels)
        points=[np.array([(index-(count-1)/2)*1.8,0,0]) for index in range(count)]
        if layout=='network':
            points=[np.array([3.1*math.cos(math.pi-2*math.pi*index/count),
                              1.65*math.sin(math.pi-2*math.pi*index/count),0]) for index in range(count)]
        self.cities=VGroup(*(Circle(radius=.28,color=theme.node,fill_color=theme.surface,
            fill_opacity=1,stroke_width=2).move_to(point) for point in points))
        self.city_labels=VGroup(*(style.math(str(label),type_role='label').move_to(city)
            for label,city in zip(labels,self.cities)))
        for city,label in zip(self.cities,labels):
            if label==r'\cdots':city.set_opacity(0)
        distances=distances or {(i,i+1):'' for i in range(count-1)}
        self.roads=VGroup();self.road_by_pair={};self.distance_labels=VGroup()
        occupied=[]
        for (i,j),distance in distances.items():
            start,end=points[i],points[j];direction=end-start
            road=Line(self.cities[i].get_boundary_point(direction),
                self.cities[j].get_boundary_point(-direction),color=theme.muted,stroke_width=1.4)
            self.roads.add(road);self.road_by_pair[tuple(sorted((i,j)))]=road
            if distance!='':
                label=style.math(str(distance),type_role='label')
                normal=np.array([-direction[1],direction[0],0])/np.linalg.norm(direction)
                candidates=[start+fraction*direction+offset*normal for fraction in (.5,.35,.65,.25,.75)
                            for offset in (.12,-.12,.25,-.25)]
                def clearance(point):
                    return min([np.linalg.norm(point-other) for other in [*points,*occupied]])
                location=max(candidates,key=clearance);occupied.append(location)
                label.move_to(location)
                self.distance_labels.add(VGroup(BackgroundRectangle(label,color=theme.background,
                    fill_opacity=1,buff=.045),label))
        self.price_labels=VGroup(*(style.math(rf'\${price}/\text{{unit}}',type_role='label')
            .next_to(city,UP,buff=.26) for city,price in zip(self.cities,prices or ())))
        self.traveler=Circle(radius=.34,color=theme.accent,stroke_width=3,fill_opacity=0)
        self.traveler.move_to(self.cities[0])
        super().__init__(self.roads,self.cities,self.city_labels,self.price_labels,
                         self.distance_labels,self.traveler)
        self.price_labels.set_opacity(0);self.distance_labels.set_opacity(0);self.traveler.set_opacity(0)
        if not show_roads:self.roads.set_opacity(0)

    def apply_scene_typography(self,typography,*,group):
        for label in [*self.city_labels,*self.price_labels,
                      *(pair[1] for pair in self.distance_labels)]:
            assign_scene_typography(label,typography,group=group,role='label')
        for label,city in zip(self.city_labels,self.cities):label.move_to(city)
        for label,city in zip(self.price_labels,self.cities):label.next_to(city,UP,buff=.26)

    def reveal_roads(self):
        self.roads.set_opacity(1)
        return AnimationGroup(*(Create(road) for road in self.roads),lag_ratio=.04)

    def reveal_distances(self):
        self.distance_labels.set_opacity(1)
        return FadeIn(self.distance_labels)

    def reveal_price(self,index):
        label=self.price_labels[index]
        label.set_opacity(1)
        return FadeIn(label)

    def start_route(self):
        self.traveler.move_to(self.cities[0])
        self.traveler.set_stroke(opacity=1).set_fill(opacity=0)
        return FadeIn(self.traveler)

    def route_step(self,start,end,*,evaluation=None):
        color=self.theme.role_color(evaluation or 'current')
        original=self.road_by_pair[tuple(sorted((start,end)))]
        highlight=original.copy().set_color(color).set_stroke(width=4)
        self.add(highlight)
        return AnimationGroup(Create(highlight),MoveAlongPath(self.traveler,
            Line(self.traveler.get_center(),self.cities[end].get_center())))

    def reset_route(self):
        return self.traveler.animate.move_to(self.cities[0])


class RoadTripSimulation(VGroup):
    """A concrete city/fuel/cost trace; values follow the supplied instance."""
    def __init__(self,*,capacity,prices,consumption,theme=DEFAULT_THEME):
        self.theme,self.capacity,self.prices,self.consumption=theme,capacity,prices,consumption
        self.city=0;self.fuel=0;self.costs=[]
        self.map=CityMap(range(1,len(consumption)+2),prices=prices,theme=theme)
        self.state=Equation({'city_label':r'\text{city: }','city':'1',
            'fuel_label':r'\quad\text{fuel: }','fuel':'0'},theme=theme)
        self.purchase=Equation({'b':r'\text{buy: }0'},theme=theme)
        self.cost=Equation({'cost':r'\text{cost}=0'},theme=theme)
        self.dashboard=VGroup(self.state,self.purchase,self.cost)
        self.dashboard.arrange(RIGHT,buff=.6).next_to(self.map,DOWN,buff=.8)
        self.pips=VGroup(*(RoundedRectangle(width=.35,height=.28,corner_radius=.04,
            color=theme.muted,fill_opacity=.15) for _ in range(capacity))).arrange(RIGHT,buff=.1)
        self.pips.next_to(self.dashboard,DOWN,buff=.3)
        # The dashboard exists geometrically but is revealed only when the
        # example starts. It must not change the map's layout when it appears.
        super().__init__(self.map,self.dashboard,self.pips)
        self.dashboard.set_opacity(0);self.pips.set_opacity(0)

    def apply_scene_typography(self,typography,*,group):
        self.map.apply_scene_typography(typography,group=group)
        for value in self.dashboard:assign_scene_typography(value,typography,group=group)
        self.dashboard.arrange(RIGHT,buff=.6).next_to(self.map,DOWN,buff=.8)
        self.pips.next_to(self.dashboard,DOWN,buff=.3)

    def start(self):
        self.dashboard.set_opacity(1)
        for pip in self.pips:pip.set_stroke(opacity=1).set_fill(opacity=.15)
        return AnimationGroup(self.map.start_route(),FadeIn(self.dashboard),FadeIn(self.pips))

    def _fuel_animation(self):
        return AnimationGroup(*(pip.animate.set_fill(self.theme.success if index<self.fuel else self.theme.surface,
            opacity=.9 if index<self.fuel else .15) for index,pip in enumerate(self.pips)))

    def buy(self,amount,*,reveal_cost=True):
        if amount<0 or self.fuel+amount>self.capacity:raise ValueError('Purchase exceeds the fuel capacity')
        self.fuel+=amount
        if amount:self.costs.append(amount*self.prices[self.city])
        target=self.purchase.next_layout(b=rf'\text{{buy: }}{amount}')
        motions=[Transform(self.purchase,target),self._fuel_animation(),
            Transform(self.state,self.state.next_layout(city=str(self.city+1),fuel=str(self.fuel)))]
        if reveal_cost:
            expression='+'.join(map(str,self.costs)) or '0'
            motions.append(Transform(self.cost,self.cost.next_layout(cost=rf'\text{{cost}}={expression}')))
        return AnimationGroup(*motions)

    def show_cost(self,*,evaluate=False):
        expression='+'.join(map(str,self.costs)) or '0'
        if evaluate:expression+='='+str(sum(self.costs))
        return Transform(self.cost,self.cost.next_layout(cost=rf'\text{{cost}}={expression}'))

    def drive(self):
        required=self.consumption[self.city]
        if self.fuel<required:raise ValueError('The demonstrated trip runs out of fuel')
        old=self.city;self.city+=1;self.fuel-=required
        return AnimationGroup(self.map.route_step(old,self.city),self._fuel_animation(),
            Transform(self.purchase,self.purchase.next_layout(b=r'\text{buy: }0')),
            Transform(self.state,self.state.next_layout(city=str(self.city+1),fuel=str(self.fuel))))
