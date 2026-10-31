import unittest
import numpy as np
from manim import RED
from algovis.core.illustrated import IllustrationImage,IllustratedItem


class IllustrationCopyTests(unittest.TestCase):
    def test_bag_and_fuel_share_capacity_layout_without_baking_state_into_the_picture(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        from algovis import IllustratedBag,IllustratedCapacity,IllustratedFuelTank,BlockScene
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'prop.png'
            Image.new('RGBA',(50,70),(40,80,140,255)).save(path)
            bag=IllustratedBag(path).with_state(capacity=2,used=1,show_meter=True)
            tank=IllustratedFuelTank(path,2).with_state(used=1,visible=True)
            for prop in (bag,tank):
                self.assertIsInstance(prop,IllustratedCapacity)
                board=BlockScene();board.add('resource',prop)
                target=prop.with_state(used=2)
                np.testing.assert_array_equal(prop.image.pixel_array,target.image.pixel_array)
                self.assertEqual(prop.used,1)
                self.assertEqual(target.meter.readout.slot_tex['used'],'2')
                self.assertGreater(target.meter.outline.get_left()[0],target.image.get_right()[0])
                with self.assertRaises(ValueError):prop.with_state(used=3)
            self.assertEqual(bag.meter.capacity_label.slot_tex['symbol'],'C')
            self.assertEqual(tank.meter.capacity_label.slot_tex['symbol'],'T')

    def test_illustrated_road_trip_gauge_stays_synced_through_compiled_actions(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        from algovis import RoadTripSimulation,ViewScene,IllustratedFuelTank
        from tests.test_composition import start,finish
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'prop.png'
            Image.new('RGBA',(50,70),(40,80,140,255)).save(path)
            trip=RoadTripSimulation(capacity=2,prices=[4,2,5],consumption=[1,1,1],tank_image=path)
            self.assertIsInstance(trip.pips,IllustratedFuelTank)
            self.assertEqual(int(trip.pips.image.pixel_array[:,:,3].max()),0)
            from algovis import (RoadTripExampleScene,ResourceExampleScene,SelectionScene,
                                 MathStack,Equation,FunctionDefinition)
            self.assertTrue(issubclass(RoadTripExampleScene,ResourceExampleScene))
            self.assertTrue(issubclass(SelectionScene,ResourceExampleScene))
            board=RoadTripExampleScene('Road Trip',context=True)
            board.add('map',trip.map,slot='map')
            board.add('tank',trip.pips,slot='tank')
            board.add('dashboard',MathStack(trip.state,trip.purchase,trip.cost),slot='dashboard')
            board.add('capacity',Equation({'capacity':'T=2'}),slot='meaning')
            board.add('roads',Equation({'roads':'g_1=g_2=g_3=1'}),slot='meaning')
            board.add('price',FunctionDefinition('p_k(b)','cost to buy b units at city k'),slot='context')
            board.validate()
            from manim import Group
            meaning=Group(board.target('capacity'),board.target('roads'))
            self.assertAlmostEqual(meaning.get_x(),board.layout.body.center[0],places=6)
            scene=ViewScene();scene.setup();scene.set_view(board)
            operations=[(trip.start,0),(lambda:trip.buy(1),1),(trip.drive,0),
                        (lambda:trip.buy(2),2),(trip.drive,1),(lambda:trip.buy(0),1),(trip.drive,0)]
            for operation,fuel in operations:
                animation=scene._compile_view(operation())
                start(animation,scene);finish(animation,scene)
                self.assertEqual(trip.fuel,fuel)
                self.assertEqual(trip.state.slot_tex['fuel'],str(fuel))
                self.assertEqual(trip.pips.used,fuel)
                self.assertEqual(trip.pips.meter.readout.slot_tex['used'],str(fuel))
                self.assertGreater(int(trip.pips.image.pixel_array[:,:,3].max()),0)
                fill=float(np.max(trip.pips.meter.fill.get_fill_opacity()))
                self.assertEqual(fill>0,fuel>0)
                self.assertEqual(trip.pips.meter.readout._algovis_type_role,'label')
                from algovis.review.inspection import capture_snapshot,typography_findings
                self.assertEqual(typography_findings(capture_snapshot(scene,14.2222222222,8.)),[])
            self.assertEqual(sum(trip.costs),8)

    def test_an_independently_animated_card_frame_stays_behind_its_contents(self):
        item=IllustratedItem(np.full((12,16,4),255,dtype=np.uint8),'item',1)
        self.assertLess(item.frame.z_index,item.image.z_index)
        self.assertLess(item.frame.z_index,item.display_name.z_index)

    def test_revealing_an_attribute_keeps_its_scene_label_role(self):
        from algovis import LessonTypography
        from algovis.layout import measured_font_size
        item=IllustratedItem(np.full((12,16,4),255,dtype=np.uint8),'item',1)
        item.apply_scene_typography(LessonTypography(),group='cards')
        updated=item.with_state(weight=1)
        self.assertEqual(updated.weight._algovis_type_role,'label')
        self.assertEqual(updated.weight.part('value')._algovis_type_role,'label')
        self.assertAlmostEqual(measured_font_size(updated.weight.part('value')),LessonTypography().label)
    def image(self):
        pixels=np.full((12,16,4),255,dtype=np.uint8)
        pixels[0,:,3]=128
        return IllustrationImage(pixels)

    def test_plans_share_pixels_but_opacity_cannot_change_another_plan(self):
        source=self.image();other=source.copy()
        self.assertIs(source.pixel_array,other.pixel_array)
        original=source.pixel_array.copy()
        other.set_opacity(.25)
        np.testing.assert_array_equal(source.pixel_array,original)
        self.assertIsNot(source.pixel_array,other.pixel_array)
        self.assertEqual(other.pixel_array[0,0,3],32)

    def test_a_color_override_detaches_from_the_source(self):
        source=self.image();other=source.copy();other.set_color(RED)
        np.testing.assert_array_equal(source.pixel_array[:,:,:3],255)
        self.assertFalse(np.array_equal(other.pixel_array,source.pixel_array))

    def test_alpha_interpolation_matches_the_native_pixel_result(self):
        source=self.image();start=source.copy().set_opacity(0);end=source.copy().set_opacity(.8)
        result=source.copy();expected=(start.pixel_array*.75+end.pixel_array*.25).astype(np.uint8)
        result.interpolate_color(start,end,.25)
        np.testing.assert_array_equal(result.pixel_array,expected)
        self.assertEqual(source.pixel_array[0,0,3],128)
